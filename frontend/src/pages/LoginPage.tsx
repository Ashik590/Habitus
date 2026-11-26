import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { PasswordField } from '../components/PasswordField'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const registration = location.state as { registeredUsername?: string; from?: string } | null
  const [username, setUsername] = useState(registration?.registeredUsername ?? '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const account = await login(username.trim(), password)
      const from = registration?.from
      const requestedPair = from?.match(/^\/practice\/([^/]+)\/([^/]+)\/exercises(?:\/\d+)?$/)
      const savedPractice = `/practice/${account.native_language.code}/${account.target_language.code}/exercises`
      const destination = requestedPair && requestedPair[1] !== account.native_language.code
        ? savedPractice
        : from?.startsWith('/') && !from.startsWith('//') ? from : '/practice'
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Login failed.')
    } finally { setSubmitting(false) }
  }

  return (
    <section className="form-card">
      <p className="eyebrow">Welcome back</p><h1>Log in</h1>
      {registration?.registeredUsername && <p role="status">Your account is ready. Log in to start practising.</p>}
      <form onSubmit={handleSubmit}>
        <label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} minLength={3} maxLength={30} autoComplete="username" autoCapitalize="none" spellCheck={false} required /></label>
        <PasswordField value={password} onChange={setPassword} autoComplete="current-password" />
        {error && <p className="form-error">{error}</p>}
        <button className="button" type="submit" disabled={submitting}>{submitting ? 'Logging in…' : 'Log in'}</button>
      </form>
      <p>New here? <Link to="/register" state={{ from: registration?.from }}>Create an account</Link>.</p>
    </section>
  )
}
