import { useEffect, useRef, useState } from 'react'
import { ApiError, api } from '../lib/api'
import type { EvaluationResponse } from '../types/api'

type RecorderStatus = 'active' | 'requesting' | 'recording' | 'evaluating' | 'complete' | 'expired'

interface AudioRecorderProps {
  languageCode: string
  exerciseId: number
  timeLimitSeconds: number
  accessToken: string | null
  onPhaseChange?: (isFinished: boolean) => void
}

const scoreMetrics: Array<[keyof EvaluationResponse, string]> = [
  ['accuracy_score', 'Accuracy'],
  ['completeness_score', 'Completeness'],
  ['grammar_score', 'Grammar'],
  ['naturalness_score', 'Naturalness'],
  ['fluency_score', 'Fluency'],
]

function chooseMimeType() {
  const candidates = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4']
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) ?? ''
}

export function AudioRecorder({
  languageCode,
  exerciseId,
  timeLimitSeconds,
  accessToken,
  onPhaseChange,
}: AudioRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>('active')
  const [remainingSeconds, setRemainingSeconds] = useState(timeLimitSeconds)
  const [feedbackLanguage, setFeedbackLanguage] = useState<'en' | 'bn'>('en')
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [error, setError] = useState('')

  const statusRef = useRef<RecorderStatus>('active')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)
  const startedAtRef = useRef<number>(Date.now())

  function updateStatus(newStatus: RecorderStatus) {
    statusRef.current = newStatus
    setStatus(newStatus)
    if (newStatus === 'evaluating' || newStatus === 'complete' || newStatus === 'expired') {
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
      clearTimer()
      if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
      releaseMicrophone()
    }
    // The recorder is remounted for each exercise. Re-running this effect for
    // callback identity changes would restart an active countdown.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exerciseId, timeLimitSeconds])

  async function evaluateRecording(audio: Blob) {
    updateStatus('evaluating')
    try {
      const evaluation = await api.evaluateExercise(
        languageCode,
        exerciseId,
        audio,
        feedbackLanguage,
        accessToken,
      )
      setResult(evaluation)
      updateStatus('complete')
    } catch (requestError) {
      const retryMessage = requestError instanceof ApiError && requestError.retryAfterSeconds
        ? ` Try again in approximately ${requestError.retryAfterSeconds} seconds.`
        : ''
      setError(
        requestError instanceof Error
          ? `${requestError.message}${retryMessage}`
          : 'Evaluation failed.',
      )
      updateStatus('expired')
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

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
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

        void evaluateRecording(audio)
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
    setError('')
    setResult(null)
    updateStatus('active')
    startSessionTimer()
  }

  const isFinished = status === 'evaluating' || status === 'complete' || status === 'expired'

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
        <div className="status-message">
          <p>Evaluating your spoken answer…</p>
        </div>
      )}

      {status === 'expired' && !result && (
        <div className="expired-card">
          <div className="expired-icon" aria-hidden="true">⏱️</div>
          <h2>Time Expired</h2>
          <p>{error || 'The countdown reached zero before an answer was recorded.'}</p>
          <div className="button-row">
            <button className="button" type="button" onClick={handleReset}>
              Try Again
            </button>
            <a className="button secondary" href={`/languages/${languageCode}/speaking/exercises`}>
              Back to Exercises
            </a>
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
          <div className="feedback-box">
            <h2>Feedback</h2>
            <p>{result.feedback}</p>
          </div>
          <div className="translations">
            <h2>Recommended translations</h2>
            <ul>
              {result.recommended_translations.map((translation) => (
                <li key={translation}>{translation}</li>
              ))}
            </ul>
          </div>
          <div className="button-row action-footer">
            <button className="button" type="button" onClick={handleReset}>
              Practice Again
            </button>
            <a className="button secondary" href={`/languages/${languageCode}/speaking/exercises`}>
              All Exercises
            </a>
          </div>
        </section>
      )}
    </div>
  )
}
