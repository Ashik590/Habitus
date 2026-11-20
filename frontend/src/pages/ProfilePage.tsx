import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
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
  const totalExercises = statistics?.level_scores.reduce(
    (total, level) => total + level.exercises_available,
    0,
  ) ?? 0
  const predictedCompetencyScore = statistics
    ? statistics.level_scores.reduce(
        (total, level) => total + (level.current_score ?? 0),
        0,
      ) / 60
    : 0
  const metricScores = statistics
    ? Object.values(statistics.dimension_averages).filter(
        (score): score is number => score !== null,
      )
    : []
  const averageMetricScore = metricScores.length > 0
    ? metricScores.reduce((total, score) => total + score, 0) / metricScores.length
    : null
  const completionRate = statistics && totalExercises > 0
    ? Math.round((statistics.exercises_completed / totalExercises) * 100)
    : 0

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
    <section className="profile-page">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">Performance overview</p>
          <h1>Learning Dashboard</h1>
          <p>Review your speaking progress and see where to focus your next practice session.</p>
        </div>
        <label className="dashboard-language-control">
          <span>Practice direction</span>
          <span className="dashboard-language-route">
            {user?.native_language.name ?? 'Source'} <b aria-hidden="true">→</b>
          </span>
          <select value={selectedTargetCode} onChange={(event) => selectLanguage(event.target.value)}>
            {targetLanguages.map((language) => (
              <option value={language.code} key={language.code}>{language.name}</option>
            ))}
          </select>
        </label>
      </header>

      <div className="profile-layout">
        <main className="profile-main">
          {error && <p className="status-message error">{error}</p>}
          {loading && !error && <p className="status-message">Loading your progress…</p>}

          {!loading && statistics && (
            <>
              <section className="dashboard-summary" aria-label="Practice summary">
                <article className="summary-card summary-card-primary">
                  <span>Exercises completed</span>
                  <div><strong>{statistics.exercises_completed}</strong><small>of {totalExercises}</small></div>
                </article>
                <article className="summary-card">
                  <span>Course completion</span>
                  <div><strong>{completionRate}%</strong><small>available practice</small></div>
                </article>
                <article className="summary-card">
                  <span>Average metric score</span>
                  <div>
                    <strong>{averageMetricScore === null ? '—' : `${averageMetricScore.toFixed(1)}%`}</strong>
                    <small>across speaking skills</small>
                  </div>
                </article>
                <article className="summary-card">
                  <span>Predicted competency</span>
                  <div>
                    <strong>{predictedCompetencyScore.toFixed(1)}<small>/10</small></strong>
                    <small>equal weight across A1–C2</small>
                  </div>
                </article>
              </section>

              <section className="analytics-section" aria-labelledby="speaking-performance-title">
                <div className="analytics-heading">
                  <div>
                    <p className="eyebrow">Spoken practice</p>
                    <h2 id="speaking-performance-title">Speaking Performance</h2>
                  </div>
                  <span className="language-pill">{selectedLanguage?.name ?? selectedTargetCode.toUpperCase()}</span>
                </div>

                <div className="dashboard-grid">
                  <article className="chart-card level-chart-card">
                    <div className="chart-heading">
                      <div>
                        <p className="chart-kicker">CEFR progression</p>
                        <h3>Performance by level</h3>
                      </div>
                      <span className="chart-caption">A1–C2</span>
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
                      <div>
                        <p className="chart-kicker">Skill profile</p>
                        <h3>Speaking metrics</h3>
                      </div>
                      <span className="chart-caption">All levels</span>
                    </div>
                    <div className="bar-chart">
                      <ScoreBar label="Accuracy" score={statistics.dimension_averages.accuracy} />
                      <ScoreBar label="Grammar" score={statistics.dimension_averages.grammar} tone="gold" />
                      <ScoreBar label="Naturalness" score={statistics.dimension_averages.naturalness} tone="gold" />
                      <ScoreBar label="Fluency" score={statistics.dimension_averages.fluency} tone="purple" />
                    </div>
                  </article>
                </div>
              </section>
            </>
          )}
        </main>

        <aside className="profile-sidebar">
          <div className="personal-info-card">
            <div className="personal-hero">
              <div className="user-avatar" aria-hidden="true">
                {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div>
                <span className="account-status">Active learner</span>
                <h3 className="profile-name">{user?.name ?? 'User Profile'}</h3>
                <p>Personal account</p>
              </div>
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
            <Link className="profile-practice-link" to="/practice">
              Continue practising <span aria-hidden="true">→</span>
            </Link>
          </div>
        </aside>
      </div>
    </section>
  )
}
