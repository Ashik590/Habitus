import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import type { EvaluationResponse } from '../types/api'

type RecorderStatus = 'idle' | 'requesting' | 'recording' | 'evaluating' | 'complete'

interface AudioRecorderProps {
  languageCode: string
  exerciseId: number
  timeLimitSeconds: number
  accessToken: string | null
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

export function AudioRecorder({ languageCode, exerciseId, timeLimitSeconds, accessToken }: AudioRecorderProps) {
  const [status, setStatus] = useState<RecorderStatus>('idle')
  const [remainingSeconds, setRemainingSeconds] = useState(timeLimitSeconds)
  const [feedbackLanguage, setFeedbackLanguage] = useState<'en' | 'bn'>('en')
  const [result, setResult] = useState<EvaluationResponse | null>(null)
  const [error, setError] = useState('')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<number | null>(null)

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

  async function evaluateRecording(audio: Blob) {
    setStatus('evaluating')
    try {
      const evaluation = await api.evaluateExercise(
        languageCode,
        exerciseId,
        audio,
        feedbackLanguage,
        accessToken,
      )
      setResult(evaluation)
      setStatus('complete')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Evaluation failed.')
      setStatus('idle')
    }
  }

  function stopRecording() {
    clearTimer()
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setError('Audio recording is not supported by this browser.')
      return
    }

    setStatus('requesting')
    setError('')
    setResult(null)
    setRemainingSeconds(timeLimitSeconds)

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
          setError('No audio was recorded. Please try again.')
          setStatus('idle')
          return
        }
        void evaluateRecording(audio)
      }

      recorder.start(250)
      setStatus('recording')
      const startedAt = Date.now()
      intervalRef.current = window.setInterval(() => {
        const elapsedSeconds = (Date.now() - startedAt) / 1000
        const remaining = Math.max(0, Math.ceil(timeLimitSeconds - elapsedSeconds))
        setRemainingSeconds(remaining)
        if (remaining === 0) stopRecording()
      }, 250)
    } catch (recordingError) {
      releaseMicrophone()
      setStatus('idle')
      setError(
        recordingError instanceof DOMException && recordingError.name === 'NotAllowedError'
          ? 'Microphone permission was denied.'
          : 'Could not start the microphone.',
      )
    }
  }

  useEffect(() => () => {
    clearTimer()
    if (recorderRef.current?.state === 'recording') recorderRef.current.stop()
    releaseMicrophone()
  }, [])

  return (
    <div className="recorder-panel">
      <div className="recorder-toolbar">
        <label>
          Feedback
          <select value={feedbackLanguage} onChange={(event) => setFeedbackLanguage(event.target.value as 'en' | 'bn')} disabled={status === 'recording' || status === 'evaluating'}>
            <option value="en">English</option>
            <option value="bn">বাংলা</option>
          </select>
        </label>
        {status === 'recording' && <strong className="countdown">{remainingSeconds}s</strong>}
      </div>

      {status === 'recording' ? (
        <button className="record-button recording" type="button" onClick={stopRecording}><span /> Stop and evaluate</button>
      ) : (
        <button className="record-button" type="button" onClick={() => void startRecording()} disabled={status === 'requesting' || status === 'evaluating'}>
          <span />{status === 'requesting' ? 'Opening microphone…' : status === 'evaluating' ? 'Evaluating your answer…' : result ? 'Record again' : 'Start recording'}
        </button>
      )}

      <p className="recorder-help">Recording stops automatically when the timer reaches zero.</p>
      {error && <p className="form-error">{error}</p>}

      {result && (
        <section className="evaluation-result" aria-live="polite">
          <div className={`overall-score ${result.is_valid_response ? '' : 'invalid'}`}>
            <span>
              {result.is_valid_response
                ? 'Overall score'
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
            {scoreMetrics.map(([key, label]) => <div key={key}><span>{label}</span><strong>{result[key] as number}</strong></div>)}
          </div>
          <div className="feedback-box"><h2>Feedback</h2><p>{result.feedback}</p></div>
          <div className="translations"><h2>Recommended translations</h2><ul>{result.recommended_translations.map((translation) => <li key={translation}>{translation}</li>)}</ul></div>
        </section>
      )}
    </div>
  )
}
