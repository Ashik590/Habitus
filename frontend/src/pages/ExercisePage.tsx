import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AudioRecorder } from '../components/AudioRecorder'
import { ExerciseAccessNotice } from '../components/ExerciseAccessNotice'
import { api, ApiError } from '../lib/api'
import type { Exercise } from '../types/api'

const languageNames: Record<string, string> = {
  bn: 'Bengali',
  en: 'English',
  de: 'German',
  es: 'Spanish',
}

interface ExerciseLoad {
  key: string
  exercise: Exercise | null
  error: string
  requiresLogin: boolean
}

export function ExercisePage() {
  const { sourceCode = 'bn', targetCode = 'en', exerciseId } = useParams()
  const { accessToken, user, isInitializing } = useAuth()
  const [load, setLoad] = useState<ExerciseLoad>({ key: '', exercise: null, error: '', requiresLogin: false })
  const [isFinished, setIsFinished] = useState(false)
  const exercisePath = `/practice/${sourceCode}/${targetCode}/exercises/${exerciseId}`
  const listPath = `/practice/${sourceCode}/${targetCode}/exercises`
  const requestKey = JSON.stringify([sourceCode, targetCode, exerciseId, user?.user_id ?? null])

  useEffect(() => {
    if (!exerciseId || isInitializing) return
    let cancelled = false
    api.getExercise(sourceCode, targetCode, exerciseId, accessToken).then((loadedExercise) => {
      if (cancelled) return
      setIsFinished(false)
      setLoad({ key: requestKey, exercise: loadedExercise, error: '', requiresLogin: false })
    }).catch((requestError: unknown) => {
      if (cancelled) return
      setLoad({
        key: requestKey,
        exercise: null,
        error: requestError instanceof Error ? requestError.message : 'Could not load this exercise.',
        requiresLogin: requestError instanceof ApiError && requestError.status === 401,
      })
    })
    return () => { cancelled = true }
  }, [accessToken, exerciseId, sourceCode, targetCode, requestKey, isInitializing])

  if (isInitializing || load.key !== requestKey) return <p className="status-message">Loading exercise…</p>
  if (load.requiresLogin) {
    return (
      <section className="practice-card">
        <ExerciseAccessNotice exercisePath={exercisePath} />
        <div className="button-row action-footer">
          <Link className="back-link" to={listPath}>← All exercises</Link>
        </div>
      </section>
    )
  }
  if (load.error) return <p className="status-message error">{load.error}</p>
  const exercise = load.exercise
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

      <p className="exercise-topic" lang={sourceCode}>#{exercise.exercise_id} · {exercise.title}</p>

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
        key={requestKey}
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
