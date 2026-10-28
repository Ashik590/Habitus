import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AudioRecorder } from '../components/AudioRecorder'
import { api } from '../lib/api'
import type { Exercise } from '../types/api'

const languageNames: Record<string, string> = {
  bn: 'Bengali',
  en: 'English',
  de: 'German',
  es: 'Spanish',
}

export function ExercisePage() {
  const { sourceCode = 'bn', targetCode = 'en', exerciseId } = useParams()
  const { accessToken } = useAuth()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [error, setError] = useState('')
  const [isFinished, setIsFinished] = useState(false)

  useEffect(() => {
    if (!exerciseId) return
    api.getExercise(sourceCode, targetCode, exerciseId, accessToken).then((loadedExercise) => {
      setIsFinished(false)
      setError('')
      setExercise(loadedExercise)
    }).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : 'Could not load this exercise.')
    })
  }, [accessToken, exerciseId, sourceCode, targetCode])

  if (error) return <p className="status-message error">{error}</p>
  if (!exercise) return <p className="status-message">Loading exercise…</p>

  const targetLanguageName = languageNames[targetCode] ?? targetCode.toUpperCase()

  return (
    <section className="practice-card">
      <div className="practice-card-top">
        <Link className="back-link" to={`/practice/${sourceCode}/${targetCode}/exercises`}>← All exercises</Link>
        <div className="practice-meta">
          <span className={`level-badge level-${exercise.level.toLowerCase()}`}>{exercise.level}</span>
          <span>{exercise.time_limit_seconds}s limit</span>
          {exercise.completed && <span>Previous score: {exercise.overall_score}</span>}
        </div>
      </div>

      {!isFinished ? (
        <div className="active-prompt-area">
          <p className="eyebrow">Translate this sentence into spoken {targetLanguageName}</p>
          <h1 className="bengali-prompt">{exercise.source_text}</h1>
        </div>
      ) : (
        <div className="finished-header">
          <p className="eyebrow">Session Ended</p>
          <h1>Evaluation & Results</h1>
        </div>
      )}

      <AudioRecorder
        sourceCode={sourceCode}
        targetCode={targetCode}
        exerciseId={exercise.exercise_id}
        timeLimitSeconds={exercise.time_limit_seconds}
        accessToken={accessToken}
        onPhaseChange={setIsFinished}
      />
    </section>
  )
}
