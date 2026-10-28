import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function AboutPage() {
  const { user } = useAuth()

  return (
    <div className="about-page">
      {/* Hero Header */}
      <header className="about-hero">
        <p className="eyebrow">About Habitus</p>
        <h1>Deliberate Practice for Genuine Spoken Fluency</h1>
        <p className="about-lead">
          Habitus is designed around a single conviction: true spoken confidence isn't built by passively tapping multiple-choice quizzes or watching videos. It is forged through active recall, vocal formulation, and immediate precision diagnostics.
        </p>
      </header>

      {/* Motto Showcase Banner */}
      <section className="motto-showcase">
        <div className="motto-badge">Our Guiding Motto</div>
        <blockquote className="motto-quote">
          “Build spoken fluency by translating from a language you know into one you are learning.”
        </blockquote>
        <p className="motto-subtext">
          Designed to bridge grammatical and expressive differences between many source and target languages.
        </p>
      </section>

      {/* Core Methodology Pillars */}
      <section className="about-section">
        <div className="section-title-wrap">
          <p className="eyebrow">The Habitus Method</p>
          <h2>How Deliberate Practice Works</h2>
        </div>
        <div className="about-grid">
          <article className="about-card">
            <div className="about-card-icon">⚡</div>
            <h3>Timed Neural Recall</h3>
            <p>
              In real conversation, you have less than two seconds to reply. Our calibrated time limits (from 15s at A1 up to 60s at C2) train your brain to bypass mental translation buffers and speak instinctively.
            </p>
          </article>

          <article className="about-card">
            <div className="about-card-icon">🎙️</div>
            <h3>Multimodal Acoustic AI</h3>
            <p>
              Habitus combines local speech recognition and voice-activity detection with Google Gemini evaluation across four quantitative dimensions: Accuracy, Grammar, Naturalness, and Fluency.
            </p>
          </article>

          <article className="about-card">
            <div className="about-card-icon">📈</div>
            <h3>The Full A1–C2 Ladder</h3>
            <p>
              Language learning shouldn't plateau at basic survival phrases. Progress continuously from foundational everyday dialogues (A1/A2) to professional workplace mastery and philosophical nuance (C1/C2).
            </p>
          </article>
        </div>
      </section>

      {/* Future Practice Vision */}
      <section className="about-section">
        <div className="section-title-wrap">
          <p className="eyebrow">The Horizon</p>
          <h2>Practice Experiences Coming in the Near Future</h2>
          <p className="section-lead-copy">
            Timed spoken translation is our current focus. Future practice experiences can broaden how learners build real-world language confidence:
          </p>
        </div>
        <div className="upcoming-practice-grid">
          <div className="upcoming-practice-card">
            <span className="upcoming-tag">Coming Soon</span>
            <div className="upcoming-icon">💬</div>
            <h3>Real-World Conversation Scenarios</h3>
            <p>Interactive situational dialogues simulating visa interviews, workplace meetings, academic seminars, and casual dinners abroad.</p>
          </div>

          <div className="upcoming-practice-card">
            <span className="upcoming-tag">Coming Soon</span>
            <div className="upcoming-icon">🎧</div>
            <h3>Accent & Native Audio Dictation</h3>
            <p>Sharpen ear-to-brain processing with native spoken accents, connected speech, elisions, and rapid comprehension drills.</p>
          </div>

          <div className="upcoming-practice-card">
            <span className="upcoming-tag">Coming Soon</span>
            <div className="upcoming-icon">🧠</div>
            <h3>Speed Collocation & Idiom Sprint</h3>
            <p>Timed high-speed drills focused on multi-word verbs, natural collocations, and prepositions that don't directly translate into Bengali.</p>
          </div>

          <div className="upcoming-practice-card">
            <span className="upcoming-tag">Coming Soon</span>
            <div className="upcoming-icon">✍️</div>
            <h3>Contextual Writing & Composition</h3>
            <p>Immediate structural feedback on writing emails, formal inquiries, and expressive personal reflections with native phrasing recommendations.</p>
          </div>
        </div>
      </section>

      {/* Developer Information */}
      <section className="about-section about-developer-section">
        <div className="section-title-wrap">
          <p className="eyebrow">Creator & Architect</p>
          <h2>Behind Habitus</h2>
        </div>
        <div className="developer-card">
          <div className="developer-avatar" aria-hidden="true">
            <span>AH</span>
          </div>
          <div className="developer-details">
            <span className="developer-role-badge">Lead Developer</span>
            <h3 className="developer-name">MD. Azizul Hakim</h3>
            <div className="developer-meta-lines">
              <p className="developer-line">BSc Student</p>
              <p className="developer-line">Institute of Information Technology</p>
              <p className="developer-line">University of Dhaka</p>
            </div>
            <div className="developer-contact">
              <span className="contact-label">Contact:</span>
              <a className="contact-link" href="mailto:bsse1634@iit.du.ac.bd">
                ✉️ bsse1634@iit.du.ac.bd
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="about-cta">
        <div className="about-cta-card">
          <h2>Ready to transform your spoken fluency?</h2>
          <p>Select your target language, test your spoken recall against calibrated timers, and see instant AI diagnostic feedback.</p>
          <div className="button-row" style={{ justifyContent: 'center', marginTop: '24px' }}>
            <Link className="button" to="/practice">
              Choose Languages & Exercises →
            </Link>
            {!user && (
              <Link className="button secondary" to="/register">
                Create Free Account
              </Link>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
