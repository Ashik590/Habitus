import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { ScoreBar } from '../components/ScoreBar'
import { api } from '../lib/api'
import type { Language, Statistics } from '../types/api'

export function ProfilePage() {
  const { accessToken, user, updateNativeLanguage } = useAuth()
  const [languages, setLanguages] = useState<Language[]>([])
  const [languageCode, setLanguageCode] = useState('en')
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch(() => undefined)
  }, [])

  const targetLanguages = languages.filter(
    (language) => language.code !== user?.native_language.code,
  )
  const selectedTargetCode = targetLanguages.some(
    (language) => language.code === languageCode,
  )
    ? languageCode
    : targetLanguages[0]?.code ?? ''

  useEffect(() => {
    if (!accessToken || !user || !selectedTargetCode) return
    api.getStatistics(user.native_language.code, selectedTargetCode, accessToken)
      .then(setStatistics)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Could not load statistics.')
      })
      .finally(() => setLoading(false))
  }, [accessToken, selectedTargetCode, user])

  const selectedLanguage = languages.find((language) => language.code === selectedTargetCode)

  function selectLanguage(code: string) {
    setLoading(true)
    setError('')
    setLanguageCode(code)
  }

  async function selectNativeLanguage(code: string) {
    setLoading(true)
    setError('')
    try {
      await updateNativeLanguage(code)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update native language.')
      setLoading(false)
    }
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
        {/* Left Column: Progress & Language Filter */}
        <div className="profile-main">
          <div className="profile-controls">
            <div className="controls-heading">
              <p className="eyebrow">Target Language</p>
              <h2>Practice Language</h2>
            </div>
            <label className="language-select">
              Language
              <select value={selectedTargetCode} onChange={(event) => selectLanguage(event.target.value)}>
                {targetLanguages.map((language) => (
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
            <div className="progress-dashboard-list">
              <section className="progress-group">
                <div className="progress-group-header">
                  <div>
                    <p className="eyebrow">Spoken Practice</p>
                    <h2>Speaking Performance</h2>
                  </div>
                  {statistics && (
                    <div className="summary-number">
                      <strong>{statistics.exercises_completed}</strong>
                      <span>exercises completed</span>
                    </div>
                  )}
                </div>

                {statistics ? (
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
                        <div><p className="eyebrow">All levels combined</p><h3>Speaking metrics</h3></div>
                        <span className="language-pill">{selectedLanguage?.name ?? selectedTargetCode.toUpperCase()}</span>
                      </div>
                      <div className="bar-chart">
                        <ScoreBar label="Accuracy" score={statistics.dimension_averages.accuracy} />
                        <ScoreBar label="Grammar" score={statistics.dimension_averages.grammar} tone="gold" />
                        <ScoreBar label="Naturalness" score={statistics.dimension_averages.naturalness} tone="gold" />
                        <ScoreBar label="Fluency" score={statistics.dimension_averages.fluency} tone="purple" />
                      </div>
                    </article>
                  </div>
                ) : null}
              </section>
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
                <dt>Native language</dt>
                <dd>
                  <select
                    value={user?.native_language.code ?? ''}
                    onChange={(event) => void selectNativeLanguage(event.target.value)}
                    disabled={!user}
                  >
                    {languages.map((language) => (
                      <option value={language.code} key={language.code}>{language.name}</option>
                    ))}
                  </select>
                </dd>
              </div>
            </dl>
          </div>
        </aside>
      </div>
    </section>
  )
}
