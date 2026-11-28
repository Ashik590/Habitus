import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../lib/api'
import type { EvaluationResponse } from '../types/api'

type RecorderStatus = 'active' | 'requesting' | 'recording' | 'evaluating' | 'complete' | 'expired' | 'failed'

interface AudioRecorderProps {
  sourceCode: string
  targetCode: string
  exerciseId: number
  timeLimitSeconds: number
  accessToken: string | null
  onPhaseChange?: (isFinished: boolean) => void
}

const scoreMetrics: Array<[keyof EvaluationResponse, string]> = [
  ['accuracy_score', 'Accuracy'],
  ['grammar_score', 'Grammar'],
  ['naturalness_score', 'Naturalness'],
  ['fluency_score', 'Fluency'],
]

function chooseMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

export function AudioRecorder({
  sourceCode,
  targetCode,
  exerciseId,
  timeLimitSeconds,
  accessToken,
  onPhaseChange,
}: AudioRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>('active')
  const [remainingSeconds, setRemainingSeconds] = useState(timeLimitSeconds)
  const [feedbackLanguage, setFeedbackLanguage] = useState<'en' | 'bn'>('en')
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [showSolutions, setShowSolutions] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [error, setError] = useState('')
  const [canRetryEvaluation, setCanRetryEvaluation] = useState(false)

  const statusRef = useRef<RecorderStatus>('active')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const startedAtRef = useRef<number>(Date.now())
  const mountedRef = useRef(false)
  const pendingRecordingRef = useRef<Blob | null>(null)

  function updateStatus(newStatus: RecorderStatus) {
    statusRef.current = newStatus
    setStatus(newStatus)
    if (newStatus === 'evaluating' || newStatus === 'complete' || newStatus === 'expired' || newStatus === 'failed') {
      onPhaseChange?.(true)
    } else {
      onPhaseChange?.(false)
    }
  }

  function clearTimer() {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }

  function releaseMicrophone() {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }

  function startSessionTimer() {
    clearTimer()
    startedAtRef.current = Date.now()
    setRemainingSeconds(timeLimitSeconds)

    intervalRef.current = window.setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000
      const remaining = Math.max(0, Math.ceil(timeLimitSeconds - elapsed))
      setRemainingSeconds(remaining)

      if (remaining === 0) {
        clearTimer()
        if (statusRef.current === 'recording') {
          stopRecording()
        } else if (statusRef.current === 'active' || statusRef.current === 'requesting') {
          releaseMicrophone()
          updateStatus('expired')
        }
      }
    }, 200)
  }

  useEffect(() => {
    mountedRef.current = true
    clearTimer()
    startedAtRef.current = Date.now()
    intervalRef.current = window.setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000
      const remaining = Math.max(0, Math.ceil(timeLimitSeconds - elapsed))
      setRemainingSeconds(remaining)

      if (remaining === 0) {
        clearTimer()
        if (statusRef.current === 'recording') {
          stopRecording()
        } else if (statusRef.current === 'active' || statusRef.current === 'requesting') {
          releaseMicrophone()
          updateStatus('expired')
        }
      }
    }, 200)
    return () => {
      mountedRef.current = false
      clearTimer()
      if (recorderRef.current) {
        // Navigation/unmount cancels the session instead of submitting it.
        recorderRef.current.onstop = null
        recorderRef.current.ondataavailable = null
        if (recorderRef.current.state !== 'inactive') recorderRef.current.stop()
      }
      releaseMicrophone()
      pendingRecordingRef.current = null
    }
    // The recorder is remounted for each exercise. Re-running this effect for
    // callback identity changes would restart an active countdown.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exerciseId, timeLimitSeconds])

  async function evaluateRecording(audio: Blob) {
    if (!mountedRef.current || statusRef.current === 'evaluating') return
    clearTimer()
    pendingRecordingRef.current = audio
    setCanRetryEvaluation(false)
    setError('')
    updateStatus('evaluating')
    try {
      const evaluation = await api.evaluateExercise(
        sourceCode,
        targetCode,
        exerciseId,
        audio,
        feedbackLanguage,
        accessToken,
      )
      if (!mountedRef.current) return
      pendingRecordingRef.current = null
      setShowSolutions(false)
      setShowFeedback(false)
      setResult(evaluation)
      updateStatus('complete')
    } catch (requestError) {
      if (!mountedRef.current) return
      const canRetry = !(requestError instanceof ApiError)
        || [408, 429, 500, 502, 503, 504].includes(requestError.status)
      setCanRetryEvaluation(canRetry)
      if (!canRetry) pendingRecordingRef.current = null
      setError(
        requestError instanceof ApiError
          ? requestError.message
          : 'We could not connect to speech evaluation. Please check your connection and try again.',
      )
      updateStatus('failed')
    }
  }

  function stopRecording() {
    clearTimer()
    if (recorderRef.current?.state === 'recording') {
      recorderRef.current.stop()
    }
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Audio recording is not supported by this browser.')
      return
    }

    updateStatus('requesting')
    setError('')
    setResult(null)
    setShowSolutions(false)
    setShowFeedback(false)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!mountedRef.current || statusRef.current !== 'requesting') {
        stream.getTracks().forEach((track) => track.stop())
        return
      }
      streamRef.current = stream
      const mimeType = chooseMimeType()
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
      const chunks: BlobPart[] = []
      recorderRef.current = recorder

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data)
      }

      recorder.onstop = () => {
        const audio = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' })
        recorderRef.current = null
        releaseMicrophone()

        if (audio.size === 0) {
          setError('No audio was captured. Session expired.')
          updateStatus('expired')
          return
        }

        if (mountedRef.current) void evaluateRecording(audio)
      }

      recorder.start(250)
      updateStatus('recording')
    } catch (recordingError) {
      releaseMicrophone()
      setError(
        recordingError instanceof DOMException && recordingError.name === 'NotAllowedError'
          ? 'Microphone permission was denied.'
          : 'Could not start the microphone.',
      )
      updateStatus('active')
    }
  }

  function handleReset() {
    clearTimer()
    releaseMicrophone()
    pendingRecordingRef.current = null
    setCanRetryEvaluation(false)
    setError('')
    setResult(null)
    setShowSolutions(false)
    setShowFeedback(false)
    updateStatus('active')
    startSessionTimer()
  }

  function retryEvaluation() {
    const audio = pendingRecordingRef.current
    if (audio && statusRef.current === 'failed') {
      void evaluateRecording(audio)
    }
  }

  const isFinished = status === 'evaluating' || status === 'complete' || status === 'expired' || status === 'failed'

  return (
    <div className="recorder-panel">
      {!isFinished && (
        <div className="countdown-banner">
          <div className="timer-info">
            <span className="eyebrow">Session Timer</span>
            <p>Speak and submit your translation before time runs out.</p>
          </div>
          <div className={`countdown-clock ${remainingSeconds <= 5 ? 'urgent' : ''}`}>
            <strong>{remainingSeconds}</strong>
            <small>sec</small>
          </div>
        </div>
      )}

      {!isFinished && (
        <div className="recorder-toolbar">
          <label>
            Feedback Language
            <select
              value={feedbackLanguage}
              onChange={(event) => setFeedbackLanguage(event.target.value as 'en' | 'bn')}
              disabled={status === 'recording'}
            >
              <option value="en">English</option>
              <option value="bn">বাংলা</option>
            </select>
          </label>
        </div>
      )}

      {status === 'recording' && (
        <button className="record-button recording" type="button" onClick={stopRecording}>
          <span /> Finish & Submit Answer
        </button>
      )}

      {(status === 'active' || status === 'requesting') && (
        <button
          className="record-button"
          type="button"
          onClick={() => void startRecording()}
          disabled={status === 'requesting'}
        >
          <span />
          {status === 'requesting' ? 'Connecting microphone…' : '🎙️ Record Answer'}
        </button>
      )}

      {status === 'evaluating' && (
        <div className="status-message evaluation-wait" role="status" aria-atomic="true">
          <p className="evaluation-wait-title">Evaluating your spoken answer…</p>
          <p className="evaluation-wait-note">
            Please allow at least 10 seconds for evaluation. It may take longer during
            busy periods. Keep this page open until your results appear.
          </p>
        </div>
      )}

      {(status === 'expired' || status === 'failed') && !result && (
        <div className={canRetryEvaluation ? 'expired-card evaluation-recovery' : 'expired-card'}>
          <div className="expired-icon" aria-hidden="true">{status === 'failed' ? '↻' : '⏱️'}</div>
          <div className="recovery-content">
            <h2>{status === 'failed'
              ? canRetryEvaluation ? 'Evaluation temporarily unavailable' : 'Evaluation unsuccessful'
              : 'Time Expired'}</h2>
            {status === 'failed' && <p className="evaluation-apology">Sorry for the interruption.</p>}
            <p>{error || 'The countdown reached zero before an answer was recorded.'}</p>
            {canRetryEvaluation && (
              <div className="recovery-recording-note">
                <strong>Your recording is ready to resubmit</strong>
                <p>No need to record again. Keep this page open to retain your recording.</p>
              </div>
            )}
            <div className="recovery-actions">
              <button className="button" type="button" onClick={canRetryEvaluation ? retryEvaluation : handleReset}>
                {canRetryEvaluation ? 'Resubmit recording' : 'Try again'}
              </button>
              {canRetryEvaluation && (
                <button className="button secondary" type="button" onClick={handleReset}>
                  Record again
                </button>
              )}
              <a className="button secondary" href={`/practice/${sourceCode}/${targetCode}/exercises`}>
                Back to exercises
              </a>
            </div>
            {canRetryEvaluation && (
              <p className="recovery-discard-note">Refreshing or leaving this page will discard your recording.</p>
            )}
          </div>
        </div>
      )}

      {result && (
        <section className="evaluation-result" aria-live="polite">
          <div className={`overall-score ${result.is_valid_response ? '' : 'invalid'}`}>
            <span>
              {result.is_valid_response
                ? 'Overall Score'
                : result.recognized_translation
                ? 'Off-topic or invalid answer'
                : 'No intelligible speech detected'}
            </span>
            <strong>{result.overall_score.toFixed(1)}</strong>
            <small>
              {result.saved
                ? 'Saved to your profile'
                : result.is_valid_response
                ? 'Log in to save your progress'
                : result.recognized_translation
                ? 'Translate the assigned sentence to earn points'
                : 'Unintelligible attempts are not saved'}
            </small>
          </div>
          <div className="recognized-answer">
            <span>Detected speech</span>
            <strong>{result.recognized_translation ? `“${result.recognized_translation}”` : 'Nothing intelligible'}</strong>
          </div>
          <div className="score-grid">
            {scoreMetrics.map(([key, label]) => (
              <div key={key}>
                <span>{label}</span>
                <strong>{result[key] as number}</strong>
              </div>
            ))}
          </div>
          <div className="button-row action-footer">
            <button
              className="button secondary result-toggle"
              type="button"
              aria-expanded={showFeedback}
              aria-controls="evaluation-feedback"
              onClick={() => setShowFeedback((visible) => !visible)}
            >
              {showFeedback ? 'Hide feedback' : 'View feedback'}
              <span className="result-toggle-chevron" aria-hidden="true" />
            </button>
          </div>
          <div
            id="evaluation-feedback"
            className={`result-disclosure${showFeedback ? ' is-open' : ''}`}
            aria-hidden={!showFeedback}
            inert={!showFeedback}
          >
            <div className="result-disclosure-content">
              <div className="feedback-box">
                <h2>Feedback</h2>
                {result.feedback.length > 0 ? (
                  <ul>
                    {result.feedback.map((problem, index) => (
                      <li key={`${index}-${problem}`}>{problem}</li>
                    ))}
                  </ul>
                ) : (
                  <p>
                    {feedbackLanguage === 'bn'
                      ? 'কোনো উল্লেখযোগ্য সমস্যা শনাক্ত করা যায়নি।'
                      : 'No significant problems detected.'}
                  </p>
                )}
              </div>
            </div>
          </div>
          {result.is_valid_response && result.recommended_translations.length > 0 && (
            <>
              <div className="button-row action-footer">
                <button
                  className="button secondary result-toggle"
                  type="button"
                  aria-expanded={showSolutions}
                  aria-controls="recommended-translations"
                  onClick={() => setShowSolutions((visible) => !visible)}
                >
                  {showSolutions
                    ? 'Hide recommended translations'
                    : 'View recommended translations'}
                  <span className="result-toggle-chevron" aria-hidden="true" />
                </button>
              </div>
              <div
                id="recommended-translations"
                className={`result-disclosure${showSolutions ? ' is-open' : ''}`}
                aria-hidden={!showSolutions}
                inert={!showSolutions}
              >
                <div className="result-disclosure-content">
                  <div className="translations">
                    <h2>Recommended translations</h2>
                    <ul>
                      {result.recommended_translations.map((translation) => (
                        <li key={translation}>{translation}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </>
          )}
          <div className="button-row action-footer">
            <button className="button" type="button" onClick={handleReset}>
              Practice Again
            </button>
            {result.saved && (
              <Link className="button secondary" to={`/practice/${sourceCode}/${targetCode}/exercises/${exerciseId}/result`}>
                View saved result
              </Link>
            )}
            <a className="button secondary" href={`/practice/${sourceCode}/${targetCode}/exercises`}>
              All Exercises
            </a>
          </div>
        </section>
      )}
    </div>
  )
}
