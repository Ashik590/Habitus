import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="home-page">
      <section className="home-hero" aria-labelledby="home-title">
        <div className="home-hero-inner">
          <div className="home-hero-content">
            <p className="eyebrow home-hero-kicker">
              <span className="badge-dot" aria-hidden="true" />
              Spoken Language Acquisition
            </p>
            <h1 id="home-title">Turn the language you know into language you speak effortlessly.</h1>
            <p className="home-hero-copy">
              Habitus builds true conversational instinct with rapid source-to-target spoken prompts,
              real-time phonetic evaluation, and precision CEFR milestones.
            </p>
            <div className="home-hero-actions">
              <Link className="button home-primary-action" to="/practice">
                Start practising <span aria-hidden="true">→</span>
              </Link>
              <Link className="button secondary" to={isAuthenticated ? '/profile' : '/register'}>
                {isAuthenticated ? 'Learning Dashboard' : 'Create free account'}
              </Link>
            </div>
            <ul className="home-hero-perks">
              <li><span aria-hidden="true">⚡</span> Timed recall drills</li>
              <li><span aria-hidden="true">🎙</span> Real-time speech evaluation</li>
              <li><span aria-hidden="true">📈</span> A1–C2 benchmarks</li>
            </ul>
          </div>

          <div className="hero-visual-stage">
            <div className="hero-visual-glow" aria-hidden="true" />
            <div className="hero-preview-card">
              <div className="preview-card-header">
                <div className="preview-language-tag">
                  <span style={{ fontSize: '1.4rem' }}>🇬🇧</span>
                  <span>English · Speaking A2</span>
                </div>
                <div className="preview-wave-indicator" aria-hidden="true">
                  <span className="soundwave-bar" />
                  <span className="soundwave-bar" />
                  <span className="soundwave-bar" />
                  <span className="soundwave-bar" />
                  <span className="soundwave-bar" />
                </div>
              </div>

              <p className="preview-prompt-label">Spoken Translation Prompt</p>
              <h2 className="preview-bengali-prompt" lang="bn">
                আমি প্রতিদিন সকালে নতুন শব্দ শিখি এবং কথা বলার অভ্যাস করি।
              </h2>

              <div className="preview-speech-bubble">
                <div className="preview-mic-icon">🎙</div>
                <p className="preview-speech-text">
                  &ldquo;I learn new words every morning and practice speaking.&rdquo;
                </p>
              </div>

              <div className="preview-score-box">
                <div className="preview-score-header">
                  <span>AI Diagnostics</span>
                  <span className="preview-overall-score">96%</span>
                </div>
                <div className="preview-score-grid">
                  <div className="preview-score-item">
                    <small>Accuracy</small>
                    <strong>98%</strong>
                  </div>
                  <div className="preview-score-item">
                    <small>Fluency</small>
                    <strong>94%</strong>
                  </div>
                  <div className="preview-score-item">
                    <small>Grammar</small>
                    <strong>97%</strong>
                  </div>
                  <div className="preview-score-item">
                    <small>Naturalness</small>
                    <strong>95%</strong>
                  </div>
                </div>
              </div>

              <div className="preview-floating-pill">
                <span>🎉</span>
                <span>CEFR A2 Cleared · Spoken Fluency</span>
              </div>
            </div>
          </div>
          <span className="home-hero-location">Mount Fuji, Japan</span>
        </div>
      </section>

      <section className="home-method home-section" aria-labelledby="home-method-title">
        <div className="home-method-heading">
          <p className="eyebrow">How it works</p>
          <h2 id="home-method-title">Read it. Say it. Refine it.</h2>
        </div>
        <ol className="home-steps">
          <li>
            <h3>Read a familiar prompt</h3>
            <p>Start with an everyday sentence in a language you know.</p>
          </li>
          <li>
            <h3>Translate it out loud</h3>
            <p>Record your answer before the timer runs out.</p>
          </li>
          <li>
            <h3>Learn from the feedback</h3>
            <p>See how you did on accuracy, grammar, naturalness, and fluency.</p>
          </li>
        </ol>
      </section>

      <section className="home-languages home-section" aria-labelledby="home-languages-title">
        <div className="home-language-copy">
          <p className="eyebrow">Your practice direction</p>
          <h2 id="home-languages-title">Choose a language pair</h2>
          <p>Begin with a language you understand, then practise expressing the same thought in one you want to speak.</p>
        </div>
        <div className="home-language-action">
          <div className="language-direction" aria-hidden="true">
            <div>
              <span>From</span>
              <strong>বাংলা</strong>
            </div>
            <span className="language-direction-arrow">→</span>
            <div>
              <span>To</span>
              <strong>English</strong>
            </div>
          </div>
          <Link className="button" to="/practice">
            Choose your languages <span aria-hidden="true">→</span>
          </Link>
        </div>
      </section>
    </div>
  )
}
