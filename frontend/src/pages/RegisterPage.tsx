import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export function RegisterPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.register(name, email, password)
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
        {error && <p className="form-error">{error}</p>}
        <button className="button" type="submit" disabled={submitting}>{submitting ? 'Creating account…' : 'Create account'}</button>
      </form>
      <p>Already registered? <Link to="/login">Log in</Link>.</p>
    </section>
  )
}
