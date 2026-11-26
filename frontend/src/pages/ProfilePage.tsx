import { useEffect, useState, type ChangeEvent } from 'react'
import { Link } from 'react-router-dom'
import defaultProfileAvatar from '../assets/default-profile-avatar.svg'
import { useAuth } from '../auth/useAuth'
import { ScoreBar } from '../components/ScoreBar'
import { api, resolveMediaUrl } from '../lib/api'
import type { Language, Statistics } from '../types/api'

export function ProfilePage() {
  const {
    accessToken,
    user,
    updateNativeLanguage,
    updateTargetLanguage,
    updateProfilePicture,
    removeProfilePicture,
  } = useAuth()
  const [languages, setLanguages] = useState<Language[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [pictureError, setPictureError] = useState('')
  const [updatingPicture, setUpdatingPicture] = useState(false)
  const [updatingLanguages, setUpdatingLanguages] = useState(false)

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch(() => undefined)
  }, [])

  const targetLanguages = languages.filter(
    (language) => language.code !== user?.native_language.code,
  )
  const selectedTargetCode = user?.target_language.code ?? ''

  useEffect(() => {
    if (!accessToken || !user || !selectedTargetCode) return
    let cancelled = false
    api.getStatistics(user.native_language.code, selectedTargetCode, accessToken)
      .then((response) => { if (!cancelled) setStatistics(response) })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : 'Could not load statistics.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [accessToken, selectedTargetCode, user])

  const selectedLanguage = languages.find((language) => language.code === selectedTargetCode)
  const profilePictureUrl = user?.profile_picture_url
    ? resolveMediaUrl(user.profile_picture_url)
    : defaultProfileAvatar
  const hasCustomProfilePicture = Boolean(user?.profile_picture_url)
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

  async function selectLanguage(code: string) {
    setLoading(true)
    setError('')
    setUpdatingLanguages(true)
    try {
      await updateTargetLanguage(code)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update target language.')
      setLoading(false)
    } finally {
      setUpdatingLanguages(false)
    }
  }

  async function selectNativeLanguage(code: string) {
    setLoading(true)
    setError('')
    setUpdatingLanguages(true)
    try {
      await updateNativeLanguage(code)
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not update native language.')
      setLoading(false)
    } finally {
      setUpdatingLanguages(false)
    }
  }

  async function handleProfilePictureChange(event: ChangeEvent<HTMLInputElement>) {
    const picture = event.target.files?.[0]
    event.target.value = ''
    if (!picture) return
    if (picture.size > 5 * 1024 * 1024) {
      setPictureError('Choose an image that is 5 MB or smaller.')
      return
    }

    setUpdatingPicture(true)
    setPictureError('')
    try {
      await updateProfilePicture(picture)
    } catch (requestError) {
      setPictureError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not update your profile picture.',
      )
    } finally {
      setUpdatingPicture(false)
    }
  }

  async function handleProfilePictureRemoval() {
    setUpdatingPicture(true)
    setPictureError('')
    try {
      await removeProfilePicture()
    } catch (requestError) {
      setPictureError(
        requestError instanceof Error
          ? requestError.message
          : 'Could not remove your profile picture.',
      )
    } finally {
      setUpdatingPicture(false)
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
          <select value={selectedTargetCode} onChange={(event) => void selectLanguage(event.target.value)} disabled={updatingLanguages}>
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
                      {statistics.level_scores.map((level) => (
                        <ScoreBar
                          key={level.level}
                          label={level.level}
                          score={level.current_score}
                          detail={`${level.exercises_completed} of ${level.exercises_available} completed`}
                          level={level.level}
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
                <img src={profilePictureUrl} alt="" />
              </div>
              <div>
                <span className="account-status">Active learner</span>
                <h3 className="profile-name">{user?.name ?? 'User Profile'}</h3>
                <p>Personal account</p>
              </div>
            </div>
            <div className="profile-photo-control">
              <div>
                <strong>Profile picture</strong>
                <span>JPEG, PNG, or WebP · 5 MB maximum</span>
              </div>
              <div className="profile-photo-actions">
                <label className="profile-photo-button">
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) => void handleProfilePictureChange(event)}
                    disabled={updatingPicture}
                  />
                  {updatingPicture
                    ? 'Updating…'
                    : hasCustomProfilePicture ? 'Change' : 'Upload'}
                </label>
                {hasCustomProfilePicture && (
                  <button
                    className="profile-photo-remove"
                    type="button"
                    onClick={() => void handleProfilePictureRemoval()}
                    disabled={updatingPicture}
                  >
                    Remove
                  </button>
                )}
              </div>
            </div>
            {pictureError && (
              <p className="profile-photo-error" role="alert">{pictureError}</p>
            )}
            <dl className="info-list">
              <div className="info-item">
                <dt>Full name</dt>
                <dd>{user?.name ?? '—'}</dd>
              </div>
              <div className="info-item">
                <dt>Username</dt>
                <dd>{user?.username ?? '—'}</dd>
              </div>
              <div className="info-item">
                <dt>Email</dt>
                <dd>{user?.email ?? 'Not provided'}</dd>
              </div>
              <div className="info-item">
                <dt>Native language</dt>
                <dd>
                  <select
                    value={user?.native_language.code ?? ''}
                    onChange={(event) => void selectNativeLanguage(event.target.value)}
                    disabled={!user || updatingLanguages}
                  >
                    {languages.map((language) => (
                      <option value={language.code} key={language.code}>{language.name}</option>
                    ))}
                  </select>
                  <p className="form-hint">Choosing your target language here swaps your practice direction.</p>
                </dd>
              </div>
              <div className="info-item">
                <dt>Target language</dt>
                <dd>
                  {user?.target_language.name ?? '—'}
                  <p className="form-hint">Change using Practice direction above.</p>
                </dd>
              </div>
            </dl>
            <Link className="profile-practice-link" to={user ? `/practice/${user.native_language.code}/${user.target_language.code}/exercises` : '/practice'}>
              Continue practising <span aria-hidden="true">→</span>
            </Link>
          </div>
        </aside>
      </div>
    </section>
  )
}
