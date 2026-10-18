import { Link } from 'react-router-dom'

export function HomePage() {
  return (
    <section className="hero-section">
      <p className="eyebrow">Practical language learning for Bangladesh</p>
      <h1>Turn the language you know into language you can use.</h1>
      <p className="hero-copy">Practice English, German, and Spanish through short Bengali-guided exercises, focused AI feedback, and clear CEFR-level progress.</p>
      <div className="button-row">
        <Link className="button" to="/languages">Choose a language</Link>
        <Link className="button secondary" to="/register">Save my progress</Link>
      </div>
      <div className="feature-grid">
        <article><strong>3</strong><span>languages to explore</span></article>
        <article><strong>5</strong><span>CEFR levels</span></article>
        <article><strong>5</strong><span>speaking dimensions</span></article>
      </div>
    </section>
  )
}
