import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { api } from '../lib/api'
import type { CefrLevel, SpeakingExercise } from '../types/api'

const levels: Array<CefrLevel | 'All'> = ['All', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const languageNames: Record<string, string> = {
  en: 'English',
  de: 'German',
  es: 'Spanish',
}

export function ExercisesPage() {
  const { languageCode = 'en' } = useParams()
  const { accessToken, isInitializing } = useAuth()
  const [selectedLevel, setSelectedLevel] = useState<CefrLevel | 'All'>('All')
  const [exercises, setExercises] = useState<SpeakingExercise[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')

  useEffect(() => {
    if (isInitializing) return

    let cancelled = false
    setLoading(true)
    setError('')
    setLoadMoreError('')
    api.getExercises(languageCode, accessToken, selectedLevel === 'All' ? undefined : selectedLevel, 0, 20)
      .then((response) => {
        if (!cancelled) {
          setExercises(response.items)
          setTotal(response.total)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : 'Could not load exercises.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [accessToken, isInitializing, languageCode, selectedLevel])

  async function handleLoadMore() {
    if (loadingMore || exercises.length >= total) return
    setLoadingMore(true)
    setLoadMoreError('')
    try {
      const response = await api.getExercises(
        languageCode,
        accessToken,
        selectedLevel === 'All' ? undefined : selectedLevel,
        exercises.length,
        20,
      )
      setExercises((prev) => [...prev, ...response.items])
      setTotal(response.total)
    } catch (err: unknown) {
      setLoadMoreError(err instanceof Error ? err.message : 'Could not load more exercises.')
    } finally {
      setLoadingMore(false)
    }
  }

  const [pendingExercise, setPendingExercise] = useState<SpeakingExercise | null>(null)

  function selectLevel(level: CefrLevel | 'All') {
    setLoading(true)
    setError('')
    setSelectedLevel(level)
  }

  const currentLanguageName = languageNames[languageCode] ?? languageCode.toUpperCase()

  return (
    <section>
      <div className="page-heading">
        <div>
          <Link className="back-link" to={`/languages/${languageCode}`}>← Language overview</Link>
          <p className="eyebrow page-kicker">{currentLanguageName} · Speaking</p>
          <h1>Exercises</h1>
          <p className="heading-copy">Select an exercise to test your spoken translation under calibrated time limits.</p>
        </div>
        <div className="level-filter" aria-label="Filter by CEFR level">
          {levels.map((level) => (
            <button className={level === selectedLevel ? 'active' : ''} key={level} type="button" onClick={() => selectLevel(level)}>{level}</button>
          ))}
        </div>
      </div>
      {loading && <p className="status-message">Loading exercises…</p>}
      {error && <p className="status-message error">{error}</p>}
      {!loading && !error && exercises.length === 0 && <p className="status-message">No exercises are available at this level.</p>}
      <div className="exercise-list">
        {exercises.map((exercise) => (
          <button
            className={`exercise-row exercise-row-btn ${exercise.completed ? 'completed' : ''}`}
            key={exercise.exercise_id}
            type="button"
            onClick={() => setPendingExercise(exercise)}
          >
            <span className={`level-badge level-${exercise.level.toLowerCase()}`}>{exercise.level}</span>
            <span className="exercise-title">
              Exercise #{exercise.exercise_id}
              <small>{exercise.time_limit_seconds}s limit</small>
            </span>
            {exercise.completed ? (
              <span className="exercise-progress completed-badge">
                ✓ {exercise.overall_score}%
              </span>
            ) : (
              <span className="exercise-progress">Not started</span>
            )}
            <span className="row-arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </div>

      {exercises.length < total && (
        <div className="load-more-container">
          <button
            className="button secondary load-more-btn"
            type="button"
            onClick={handleLoadMore}
            disabled={loadingMore}
          >
            {loadingMore ? 'Loading more exercises…' : `Show more exercises (${exercises.length} of ${total})`}
          </button>
          {loadMoreError && <p className="status-message error load-more-error">{loadMoreError}</p>}
        </div>
      )}

      {pendingExercise && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="modal-card">
            <div className="modal-header">
              <span className={`level-badge level-${pendingExercise.level.toLowerCase()}`}>{pendingExercise.level}</span>
              <p className="eyebrow">Timed Practice Session</p>
            </div>
            <h2 id="modal-title">Exercise #{pendingExercise.exercise_id}</h2>
            <div className="modal-body">
              <p>
                Once you begin, the <strong>{pendingExercise.time_limit_seconds}-second countdown</strong> starts immediately.
              </p>
              <p className="modal-hint">
                Formulate your translation and record your answer before the clock reaches zero. The prompt will disappear when the timer ends.
              </p>
            </div>
            <div className="modal-actions">
              <button className="button secondary" type="button" onClick={() => setPendingExercise(null)}>
                Cancel
              </button>
              <Link
                className="button"
                to={`/languages/${languageCode}/speaking/exercises/${pendingExercise.exercise_id}`}
                onClick={() => setPendingExercise(null)}
              >
                I'm Ready · Start
              </Link>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
