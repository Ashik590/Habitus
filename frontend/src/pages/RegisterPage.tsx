import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { Language } from '../types/api'

export function RegisterPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nativeLanguageCode, setNativeLanguageCode] = useState('bn')
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
    setSubmitting(true)
    setError('')
    try {
      await api.register(name, email, password, nativeLanguageCode)
      navigate('/login', { replace: true })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Registration failed.')
    } finally { setSubmitting(false) }
  }

  return (
    <section className="form-card">
      <p className="eyebrow">Track your progress</p><h1>Create account</h1>
      <form onSubmit={handleSubmit}>
        <label>Name<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} required /></label>
        <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={8} required /></label>
        <label>
          Native language
          <select value={nativeLanguageCode} onChange={(event) => setNativeLanguageCode(event.target.value)} required>
            {languages.map((language) => (
              <option value={language.code} key={language.code}>{language.name}</option>
            ))}
          </select>
        </label>
        <p className="form-hint">This becomes the source language for your signed-in practice. You can change it later.</p>
        {error && <p className="form-error">{error}</p>}
        <button className="button" type="submit" disabled={submitting || languages.length === 0}>{submitting ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p>Already registered? <Link to="/login">Log in</Link>.</p>
    </section>
  )
}

