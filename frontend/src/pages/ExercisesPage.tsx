import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ExerciseAccessNotice, ExerciseLockIcon } from '../components/ExerciseAccessNotice'
import { api } from '../lib/api'
import type { CefrLevel, ExerciseSummary } from '../types/api'

const levels: Array<CefrLevel | 'All'> = ['All', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const languageNames: Record<string, string> = {
  bn: 'Bengali',
  en: 'English',
  de: 'German',
  es: 'Spanish',
}

export function ExercisesPage() {
  const { sourceCode = 'bn', targetCode = 'en' } = useParams()
  const { accessToken, isInitializing, user } = useAuth()
  const [selectedLevel, setSelectedLevel] = useState<CefrLevel | 'All'>('All')
  const [exercises, setExercises] = useState<ExerciseSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [loadMoreError, setLoadMoreError] = useState('')

  useEffect(() => {
    if (isInitializing) return

    let cancelled = false
    api.getExercises(sourceCode, targetCode, accessToken, selectedLevel === 'All' ? undefined : selectedLevel, 0, 20)
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
  }, [accessToken, isInitializing, selectedLevel, sourceCode, targetCode])

  async function handleLoadMore() {
    if (loadingMore || exercises.length >= total) return
    setLoadingMore(true)
    setLoadMoreError('')
    try {
      const response = await api.getExercises(
        sourceCode,
        targetCode,
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

  const [pendingExercise, setPendingExercise] = useState<ExerciseSummary | null>(null)
  const pendingIsLocked = pendingExercise !== null && !user
    && (pendingExercise.is_locked || !pendingExercise.is_public)

  function selectLevel(level: CefrLevel | 'All') {
    setLoading(true)
    setError('')
    setSelectedLevel(level)
  }

  const sourceLanguageName = languageNames[sourceCode] ?? sourceCode.toUpperCase()
  const targetLanguageName = languageNames[targetCode] ?? targetCode.toUpperCase()

  return (
    <section>
      <div className="page-heading">
        <div>
          <Link className="back-link" to={user ? '/profile' : '/practice'}>
            {user ? '← Language preferences' : '← Change languages'}
          </Link>
          <p className="eyebrow page-kicker">{sourceLanguageName} → {targetLanguageName}</p>
          <h1>Exercises</h1>
          <p className="heading-copy">Select an exercise to test your spoken translation under calibrated time limits.</p>
          {!user && <p className="form-hint">Try the public samples, or sign in to unlock all exercises.</p>}
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
        {exercises.map((exercise) => {
          const isLocked = !user && (exercise.is_locked || !exercise.is_public)
          return (
            <button
              className={`exercise-row exercise-row-btn ${user && exercise.completed ? 'completed' : ''} ${isLocked ? 'locked' : ''}`}
              key={exercise.exercise_id}
              type="button"
              onClick={() => setPendingExercise(exercise)}
              aria-label={isLocked ? `Exercise #${exercise.exercise_id}: ${exercise.title}, ${exercise.level}, sign in required` : undefined}
            >
              <span className={`level-badge level-${exercise.level.toLowerCase()}`}>{exercise.level}</span>
              <span className="exercise-title">
                <span className="exercise-name" lang={sourceCode}>#{exercise.exercise_id} · {exercise.title}</span>
                <small>{exercise.time_limit_seconds}s limit</small>
              </span>
              {user && (exercise.completed ? (
                <span className="exercise-progress completed-badge">
                  ✓ {exercise.overall_score}%
                </span>
              ) : (
                <span className="exercise-progress">Not started</span>
              ))}
              <span className="row-arrow" aria-hidden="true">{isLocked ? <ExerciseLockIcon /> : '→'}</span>
            </button>
          )
        })}
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
            {pendingIsLocked ? (
              <>
                <ExerciseAccessNotice
                  headingId="modal-title"
                  exercisePath={`/practice/${sourceCode}/${targetCode}/exercises/${pendingExercise.exercise_id}`}
                />
                <div className="modal-actions">
                  <button className="button secondary" type="button" onClick={() => setPendingExercise(null)}>Back to exercises</button>
                </div>
              </>
            ) : (
              <>
                <div className="modal-header">
                  <span className={`level-badge level-${pendingExercise.level.toLowerCase()}`}>{pendingExercise.level}</span>
                  <p className="eyebrow">{user && pendingExercise.completed ? 'Completed exercise' : 'Timed Practice Session'}</p>
                </div>
                <h2 id="modal-title" className="exercise-topic" lang={sourceCode}>#{pendingExercise.exercise_id} · {pendingExercise.title}</h2>
                <div className="modal-body">
                  {user && pendingExercise.completed && (
                    <p>Your latest score is <strong>{pendingExercise.overall_score}%</strong>. Review your saved result or practise again. A new valid result replaces the previous one.</p>
                  )}
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
                  {user && pendingExercise.completed && (
                    <Link
                      className="button"
                      to={`/practice/${sourceCode}/${targetCode}/exercises/${pendingExercise.exercise_id}/result`}
                      onClick={() => setPendingExercise(null)}
                    >
                      View result
                    </Link>
                  )}
                  <Link
                    className={user && pendingExercise.completed ? 'button secondary' : 'button'}
                    to={`/practice/${sourceCode}/${targetCode}/exercises/${pendingExercise.exercise_id}`}
                    onClick={() => setPendingExercise(null)}
                  >
                    {user && pendingExercise.completed ? 'Practise again' : "I'm Ready · Start"}
                  </Link>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
