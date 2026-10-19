import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <section className="hero-section">
      <p className="eyebrow">Make language your second nature</p>
      <h1>Turn the language you know into language you can use.</h1>
      <p className="hero-copy">Practice through guided exercises, instant feedback, and clear CEFR-level progress.</p>
      <div className="button-row">
        <Link className="button" to="/languages">Choose a language</Link>
        <Link className="button secondary" to="/register">Create account</Link>
      </div>
      <div className="feature-grid">
        <article><strong>Multiple</strong><span>languages to explore</span></article>
        <article><strong>A1–C1</strong><span>CEFR levels</span></article>
        <article><strong>Instant</strong><span>AI feedback & metrics</span></article>
      </div>
    </section>
  )
}
