import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AudioRecorder } from '../components/AudioRecorder'
import { api } from '../lib/api'
import type { SpeakingExercise } from '../types/api'

const languageNames: Record<string, string> = {
  en: 'English',
  de: 'German',
  es: 'Spanish',
}

export function ExercisePage() {
  const { languageCode = 'en', exerciseId } = useParams()
  const { accessToken } = useAuth()
  const [exercise, setExercise] = useState<SpeakingExercise | null>(null)
  const [error, setError] = useState('')
  const [isFinished, setIsFinished] = useState(false)

  useEffect(() => {
    if (!exerciseId) return
    setIsFinished(false)
    api.getExercise(languageCode, exerciseId, accessToken).then(setExercise).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : 'Could not load this exercise.')
    })
  }, [accessToken, exerciseId, languageCode])

  if (error) return <p className="status-message error">{error}</p>
  if (!exercise) return <p className="status-message">Loading exercise…</p>

  const targetLanguageName = languageNames[languageCode] ?? languageCode.toUpperCase()

  return (
    <section className="practice-card">
      <div className="practice-card-top">
        <Link className="back-link" to={`/languages/${languageCode}/speaking/exercises`}>← All speaking exercises</Link>
        <div className="practice-meta">
          <span className={`level-badge level-${exercise.level.toLowerCase()}`}>{exercise.level}</span>
          <span>{exercise.time_limit_seconds}s limit</span>
          {exercise.completed && <span>Previous score: {exercise.overall_score}</span>}
        </div>
      </div>

      {!isFinished ? (
        <div className="active-prompt-area">
          <p className="eyebrow">Translate this sentence into spoken {targetLanguageName}</p>
          <h1 lang="bn" className="bengali-prompt">{exercise.bengali_text}</h1>
        </div>
      ) : (
        <div className="finished-header">
          <p className="eyebrow">Session Ended</p>
          <h1>Evaluation & Results</h1>
        </div>
      )}

      <AudioRecorder
        languageCode={languageCode}
        exerciseId={exercise.exercise_id}
        timeLimitSeconds={exercise.time_limit_seconds}
        accessToken={accessToken}
        onPhaseChange={setIsFinished}
      />
    </section>
  )
}
