import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div>
      {/* 2-Column Hero Section */}
      <section className="hero-layout">
        <div className="hero-content">
          <div className="hero-pill">
            <span className="badge-dot" />
            <span>Spoken Language Acquisition</span>
          </div>
          <h1>Turn the language you know into language you speak effortlessly.</h1>
          <p className="hero-copy">
            Habitus builds true conversational instinct with rapid source-to-target spoken prompts,
            real-time phonetic evaluation, and precision CEFR milestones.
          </p>
          <div className="hero-actions">
            <Link className="button" to="/practice">
              Start practising →
            </Link>
            {isAuthenticated ? (
              <Link className="button secondary" to="/profile">
                Learning Dashboard
              </Link>
            ) : (
              <Link className="button secondary" to="/register">
                Create free account
              </Link>
            )}
          </div>
          <div className="hero-perks">
            <span>⚡ Timed recall drills</span>
            <span>🎙 Real-time speech evaluation</span>
            <span>📈 A1–C2 benchmarks</span>
          </div>
        </div>

        {/* Hero Visual Preview */}
        <div className="hero-visual-stage">
          <div className="hero-visual-glow" aria-hidden="true" />
          <div className="hero-preview-card">
            <div className="preview-card-header">
              <div className="preview-language-tag">
                <span style={{ fontSize: '1.4rem' }}>🇬🇧</span>
                <span>English · Speaking A2</span>
              </div>
              <div className="preview-wave-indicator" title="Audio waveform activity">
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
      </section>

      {/* How it Works Section */}
      <section>
        <div className="home-section-header">
          <p className="eyebrow">The Method</p>
          <h2>Deliberate practice for involuntary fluency</h2>
          <p>
            Most learners can read but freeze when speaking. Habitus bridges the gap through timed
            spontaneous translation and calibrated feedback.
          </p>
        </div>

        <div className="how-it-works-grid">
          <article className="how-it-works-card">
            <div className="how-step-num">01</div>
            <h3>Read a Familiar Prompt</h3>
            <p>
              Encounter natural everyday sentences in a language you know. Your brain must immediately synthesize the
              translation without multiple-choice crutches.
            </p>
          </article>
          <article className="how-it-works-card">
            <div className="how-step-num">02</div>
            <h3>Speak Under Time Limits</h3>
            <p>
              Speak your answer directly into your microphone before the timer runs out, simulating authentic
              conversational pacing and recall pressure.
            </p>
          </article>
          <article className="how-it-works-card">
            <div className="how-step-num">03</div>
            <h3>Instant Diagnostic Feedback</h3>
            <p>
              Receive instant scores across 4 core dimensions: accuracy, grammar, naturalness,
              and speech fluency.
            </p>
          </article>
        </div>
      </section>

      {/* Languages Preview Strip */}
      <section>
        <div className="languages-preview-header">
          <div>
            <p className="eyebrow">Available Languages</p>
            <h2>Choose your target language</h2>
          </div>
          <Link className="back-link" to="/practice">
            Choose your languages →
          </Link>
        </div>

        <div className="language-grid">
          <Link className="language-card" to="/practice">
            <div>
              <div className="language-flag">🇬🇧</div>
              <h2>English</h2>
              <p className="language-native">ইংরেজি ভাষা চর্চা</p>
              <p>Practice spoken fluency across everyday conversations, workplace communication, and idioms.</p>
            </div>
            <div className="card-arrow">→</div>
          </Link>

          <Link className="language-card" to="/practice">
            <div>
              <div className="language-flag">🇩🇪</div>
              <h2>German</h2>
              <p className="language-native">জার্মান ভাষা চর্চা</p>
              <p>Master German sentence structures, cases, and spoken clarity from A1 survival to C2 mastery.</p>
            </div>
            <div className="card-arrow">→</div>
          </Link>

          <Link className="language-card" to="/practice">
            <div>
              <div className="language-flag">🇪🇸</div>
              <h2>Spanish</h2>
              <p className="language-native">স্প্যানিশ ভাষা চর্চা</p>
              <p>Train your spoken tempo, expressive verb conjugations, and natural everyday dialogue.</p>
            </div>
            <div className="card-arrow">→</div>
          </Link>
        </div>
      </section>
    </div>
  )
}
