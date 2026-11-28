import { useEffect, useId, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { api } from '../lib/api'
import type { SavedEvaluation } from '../types/api'

const metrics = [
  ['accuracy_score', 'Accuracy'],
  ['grammar_score', 'Grammar'],
  ['naturalness_score', 'Naturalness'],
  ['fluency_score', 'Fluency'],
] as const

function ResultDisclosure({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <>
      <div className="button-row action-footer">
        <button className="button secondary result-toggle" type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen((value) => !value)}>
          {open ? 'Hide' : 'View'} {label}
          <span className="result-toggle-chevron" aria-hidden="true" />
        </button>
      </div>
      <div id={id} className={`result-disclosure${open ? ' is-open' : ''}`} aria-hidden={!open} inert={!open}>
        <div className="result-disclosure-content">{children}</div>
      </div>
    </>
  )
}

export function ExerciseResultPage() {
  const { sourceCode = 'bn', targetCode = 'en', exerciseId } = useParams()
  const { accessToken, user } = useAuth()
  const key = JSON.stringify([sourceCode, targetCode, exerciseId, user?.user_id])
  const [load, setLoad] = useState<{ key: string; result: SavedEvaluation | null; error: string }>({ key: '', result: null, error: '' })
  const exercisePath = `/practice/${sourceCode}/${targetCode}/exercises/${exerciseId}`
  const listPath = `/practice/${sourceCode}/${targetCode}/exercises`

  useEffect(() => {
    if (!exerciseId || !accessToken) return
    let cancelled = false
    api.getSavedResult(sourceCode, targetCode, exerciseId, accessToken)
      .then((result) => { if (!cancelled) setLoad({ key, result, error: '' }) })
      .catch((error: unknown) => {
        if (!cancelled) setLoad({ key, result: null, error: error instanceof Error ? error.message : 'Could not load your saved result.' })
      })
    return () => { cancelled = true }
  }, [sourceCode, targetCode, exerciseId, accessToken, key])

  if (load.key !== key) return <p className="status-message">Loading saved result…</p>
  if (load.error || !load.result) return (
    <section className="practice-card">
      <h1>Saved result unavailable</h1>
      <p className="status-message error">{load.error || 'No saved result found.'}</p>
      <Link className="back-link" to={listPath}>← All exercises</Link>
    </section>
  )
  return <SavedResult key={key} result={load.result} sourceCode={sourceCode} targetCode={targetCode} exercisePath={exercisePath} listPath={listPath} />
}

function SavedResult({ result, sourceCode, targetCode, exercisePath, listPath }: {
  result: SavedEvaluation; sourceCode: string; targetCode: string; exercisePath: string; listPath: string
}) {
  const completedDate = result.completed_at ? new Date(result.completed_at) : null
  return (
    <section className="practice-card saved-result">
      <div className="practice-card-top">
        <Link className="back-link" to={listPath}>← All exercises</Link>
        <div className="practice-meta">
          <span className={`level-badge level-${result.level.toLowerCase()}`}>{result.level}</span>
          <span>{result.time_limit_seconds}s limit</span>
        </div>
      </div>
      <p className="exercise-topic" lang={sourceCode}>#{result.exercise_id} · {result.title}</p>
      <p className="eyebrow">Latest completed attempt</p>
      <h1>Your saved result</h1>
      <p className="form-hint">
        {completedDate ? (
          <>Completed <time dateTime={result.completed_at ?? undefined}>{new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'long' }).format(completedDate)}</time></>
        ) : 'Completion time was not recorded for this older result.'}
      </p>
      <div className="recognized-answer saved-result-source">
        <span>Source sentence</span>
        <strong lang={sourceCode}>{result.source_text}</strong>
      </div>
      <div className="evaluation-result">
        <div className="overall-score">
          <span>Overall score</span><strong>{result.overall_score.toFixed(1)}</strong><small>Out of 100</small>
        </div>
        <div className="recognized-answer">
          <span>Detected speech</span>
          {result.recognized_translation !== null
            ? <strong lang={targetCode}>“{result.recognized_translation}”</strong>
            : <p className="form-hint">Speech was not saved with this older result. Complete the exercise again to save it.</p>}
        </div>
        <div className="score-grid">
          {metrics.map(([metric, label]) => <div key={metric}><span>{label}</span><strong>{result[metric]}</strong></div>)}
        </div>
        <ResultDisclosure label="feedback">
          <div className="feedback-box">
            <h2>Feedback</h2>
            {result.feedback === null ? <p>Feedback was not saved with this older result. Complete the exercise again to save it.</p>
              : result.feedback.length ? <ul>{result.feedback.map((item, index) => <li key={index}>{item}</li>)}</ul>
                : <p>No significant problems detected.</p>}
          </div>
        </ResultDisclosure>
        <ResultDisclosure label="preferred solutions">
          <div className="translations">
            <h2>Preferred solutions</h2>
            {result.preferred_solutions.length ? <ul lang={targetCode}>{result.preferred_solutions.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>No preferred solutions have been added for this exercise.</p>}
          </div>
        </ResultDisclosure>
        <p className="form-hint saved-result-note">Only your latest valid result is kept. Completing this exercise again replaces it.</p>
        <div className="button-row action-footer">
          <Link className="button" to={exercisePath}>Practise again</Link>
          <Link className="button secondary" to={listPath}>All exercises</Link>
        </div>
      </div>
    </section>
  )
}
