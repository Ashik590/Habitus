import { useEffect, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { PasswordField } from '../components/PasswordField'
import { api } from '../lib/api'
import type { Language } from '../types/api'

const VALID_NAME_CHARACTERS = /^[\p{L}\p{M} .'’-]+$/u

function normalizeName(value: string) {
  return value.trim().replace(/\s+/g, ' ')
}

function isValidName(value: string) {
  const normalizedName = normalizeName(value)
  const letterCount = normalizedName.match(/\p{L}/gu)?.length ?? 0
  return letterCount >= 2
    && VALID_NAME_CHARACTERS.test(normalizedName)
    && /^\p{L}/u.test(normalizedName)
    && /[\p{L}\p{M}]$/u.test(normalizedName)
}

export function RegisterPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const entry = location.state as { from?: string } | null
  const requestedPair = entry?.from?.match(/^\/practice\/([^/]+)\/([^/]+)\/exercises\/\d+$/)
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nativeLanguageCode, setNativeLanguageCode] = useState(requestedPair?.[1] ?? 'bn')
  const [targetLanguageCode, setTargetLanguageCode] = useState(requestedPair?.[2] ?? 'en')
  const [languages, setLanguages] = useState<Language[]>([])
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : 'Could not load languages.')
    })
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const normalizedName = normalizeName(name)
    const normalizedUsername = username.trim().toLowerCase()
    if (!isValidName(normalizedName)) {
      setError('Enter a valid name using letters, spaces, apostrophes, periods, or hyphens.')
      return
    }
    if (!/^[a-z][a-z0-9_]{2,29}$/.test(normalizedUsername)) {
      setError('Username must be 3–30 characters, start with a letter, and contain only English letters, numbers, or underscores.')
      return
    }
    if (!targetLanguageCode || targetLanguageCode === nativeLanguageCode) {
      setError('Choose a target language different from your native language.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const account = await api.register({
        name: normalizedName,
        username: normalizedUsername,
        email: email.trim() || null,
        password,
        native_language_code: nativeLanguageCode,
        target_language_code: targetLanguageCode,
      })
      navigate('/login', { replace: true, state: { registeredUsername: account.username, from: entry?.from } })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Registration failed.')
    } finally { setSubmitting(false) }
  }

  return (
    <section className="form-card">
      <p className="eyebrow">Track your progress</p><h1>Create account</h1>
      <p className="form-hint"><span className="required-mark" aria-hidden="true">*</span> Required fields</p>
      <form onSubmit={handleSubmit}>
        <label><span>Full name <span className="required-mark" aria-hidden="true">*</span></span><input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={100} autoComplete="name" required /></label>
        <label>
          <span>Username <span className="required-mark" aria-hidden="true">*</span></span>
          <input value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} maxLength={30} autoComplete="username" autoCapitalize="none" spellCheck={false} aria-describedby="username-hint" required />
        </label>
        <p className="form-hint" id="username-hint">Use 3–30 English letters, numbers, or underscores. Start with a letter. Usernames are case-insensitive.</p>
        <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} maxLength={320} autoComplete="email" /></label>
        <PasswordField value={password} onChange={setPassword} autoComplete="new-password" minLength={8} showRequiredMark />
        <label>
          <span>Native language <span className="required-mark" aria-hidden="true">*</span></span>
          <select value={nativeLanguageCode} onChange={(event) => {
            const code = event.target.value
            setNativeLanguageCode(code)
            if (targetLanguageCode === code) setTargetLanguageCode('')
          }} required>
            {languages.map((language) => (
              <option value={language.code} key={language.code}>{language.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Target language <span className="required-mark" aria-hidden="true">*</span></span>
          <select value={targetLanguageCode} onChange={(event) => setTargetLanguageCode(event.target.value)} required>
            <option value="" disabled>Choose the language you want to learn</option>
            {languages.filter((language) => language.code !== nativeLanguageCode).map((language) => (
              <option value={language.code} key={language.code}>{language.name}</option>
            ))}
          </select>
        </label>
        <p className="form-hint">Practice opens directly in your chosen language pair. You can change these preferences in your dashboard.</p>
        {error && <p className="form-error">{error}</p>}
        <button className="button" type="submit" disabled={submitting || languages.length < 2}>{submitting ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p>Already registered? <Link to="/login" state={{ from: entry?.from }}>Log in</Link>.</p>
    </section>
  )
}

