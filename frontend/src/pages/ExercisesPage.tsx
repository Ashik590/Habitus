import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { api } from '../lib/api'
import type { CefrLevel, SpeakingExercise } from '../types/api'

const levels: Array<CefrLevel | 'All'> = ['All', 'A1', 'A2', 'B1', 'B2', 'C1']

export function ExercisesPage() {
  const { languageCode = 'en' } = useParams()
  const { accessToken } = useAuth()
  const [selectedLevel, setSelectedLevel] = useState<CefrLevel | 'All'>('All')
  const [exercises, setExercises] = useState<SpeakingExercise[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    api.getExercises(languageCode, accessToken, selectedLevel === 'All' ? undefined : selectedLevel)
      .then((response) => { if (!cancelled) setExercises(response.items) })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : 'Could not load exercises.')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [accessToken, languageCode, selectedLevel])

  function selectLevel(level: CefrLevel | 'All') {
    setLoading(true)
    setError('')
    setSelectedLevel(level)
  }

  return (
    <section>
      <div className="page-heading">
        <div><Link className="back-link" to={`/languages/${languageCode}`}>← Language overview</Link><p className="eyebrow page-kicker">Speaking module · {languageCode.toUpperCase()}</p><h1>Exercises</h1><p className="heading-copy">Choose a level and translate each Bengali prompt aloud.</p></div>
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
          <Link className="exercise-row" key={exercise.exercise_id} to={`/languages/${languageCode}/speaking/exercises/${exercise.exercise_id}`}>
            <span className={`level-badge level-${exercise.level.toLowerCase()}`}>{exercise.level}</span>
            <span className="exercise-title">Exercise {exercise.exercise_id}<small>{exercise.time_limit_seconds} seconds</small></span>
            <span className="exercise-progress">{exercise.completed ? `${exercise.overall_score} score` : 'Not completed'}</span>
            <span aria-hidden="true">→</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
