import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { ScoreBar } from '../components/ScoreBar'
import { api } from '../lib/api'
import type { Language, LearningModule, SpeakingStatistics } from '../types/api'

export function ProfilePage() {
  const { accessToken, user } = useAuth()
  const [languages, setLanguages] = useState<Language[]>([])
  const [modules, setModules] = useState<LearningModule[]>([])
  const [languageCode, setLanguageCode] = useState('en')
  const [statistics, setStatistics] = useState<SpeakingStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch(() => undefined)
    api.getModules().then(setModules).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!accessToken) return
    api.getStatistics(languageCode, accessToken)
      .then(setStatistics)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Could not load statistics.')
      })
      .finally(() => setLoading(false))
  }, [accessToken, languageCode])

  const selectedLanguage = languages.find((language) => language.code === languageCode)

  function selectLanguage(code: string) {
    setLoading(true)
    setError('')
    setLanguageCode(code)
  }

  return (
    <section>
      <div className="profile-header">
        <div>
          <p className="eyebrow">Profile</p>
          <h1>Learning Dashboard</h1>
          <p>Track your speaking performance, CEFR milestones, and personal details.</p>
        </div>
      </div>

      <div className="profile-layout">
        {/* Left Column: Modules & Language Filter */}
        <div className="profile-main">
          <div className="profile-controls">
            <div className="controls-heading">
              <p className="eyebrow">Target Language</p>
              <h2>Practice Language</h2>
            </div>
            <label className="language-select">
              Language
              <select value={languageCode} onChange={(event) => selectLanguage(event.target.value)}>
                {languages.map((language) => (
                  <option value={language.code} key={language.code}>
                    {language.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error && <p className="status-message error">{error}</p>}
          {loading && !error && <p className="status-message">Loading your progress…</p>}

          {!loading && (
            <div className="modules-dashboard-list">
              {modules.map((module) => {
                const isSpeaking = module.code === 'speaking'
                return (
                  <section className="module-group" key={module.code}>
                    <div className="module-group-header">
                      <div>
                        <p className="eyebrow">Module</p>
                        <h2>{module.name}</h2>
                      </div>
                      {isSpeaking && statistics && (
                        <div className="summary-number">
                          <strong>{statistics.exercises_completed}</strong>
                          <span>exercises completed</span>
                        </div>
                      )}
                    </div>

                    {isSpeaking && statistics ? (
                      <div className="dashboard-grid">
                        <article className="chart-card level-chart-card">
                          <div className="chart-heading">
                            <div><p className="eyebrow">Current score</p><h3>Performance by level</h3></div>
                          </div>
                          <div className="bar-chart">
                            {statistics.level_scores.map((level, index) => (
                              <ScoreBar
                                key={level.level}
                                label={level.level}
                                score={level.current_score}
                                detail={`${level.exercises_completed} of ${level.exercises_available} completed`}
                                tone={index >= 4 ? 'purple' : index >= 2 ? 'gold' : 'rose'}
                              />
                            ))}
                          </div>
                        </article>

                        <article className="chart-card dimension-chart-card">
                          <div className="chart-heading">
                            <div><p className="eyebrow">All levels combined</p><h3>{module.name} metrics</h3></div>
                            <span className="language-pill">{selectedLanguage?.name ?? languageCode.toUpperCase()}</span>
                          </div>
                          <div className="bar-chart">
                            <ScoreBar label="Accuracy" score={statistics.dimension_averages.accuracy} />
                            <ScoreBar label="Completeness" score={statistics.dimension_averages.completeness} />
                            <ScoreBar label="Grammar" score={statistics.dimension_averages.grammar} tone="gold" />
                            <ScoreBar label="Naturalness" score={statistics.dimension_averages.naturalness} tone="gold" />
                            <ScoreBar label="Fluency" score={statistics.dimension_averages.fluency} tone="purple" />
                          </div>
                        </article>
                      </div>
                    ) : (
                      <div className="module-coming-soon-card">
                        <p>{module.name} module is coming soon.</p>
                      </div>
                    )}
                  </section>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Personal Information Sidebar */}
        <aside className="profile-sidebar">
          <div className="personal-info-card">
            <div className="personal-hero">
              <div className="user-avatar" aria-hidden="true">
                {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <h3 className="profile-name">{user?.name ?? 'User Profile'}</h3>
            </div>
            <dl className="info-list">
              <div className="info-item">
                <dt>Full name</dt>
                <dd>{user?.name ?? '—'}</dd>
              </div>
              <div className="info-item">
                <dt>Email</dt>
                <dd>{user?.email ?? '—'}</dd>
              </div>
              <div className="info-item">
                <dt>Phone</dt>
                <dd>+880 1700-000000</dd>
              </div>
              <div className="info-item">
                <dt>Location</dt>
                <dd>Dhaka, Bangladesh</dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
    </section>
  )
}
