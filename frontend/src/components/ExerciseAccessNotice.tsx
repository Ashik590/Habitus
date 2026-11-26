import { Link } from 'react-router-dom'

export function ExerciseLockIcon() {
  return (
    <svg className="exercise-lock-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="5" y="10" width="14" height="11" rx="3" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3" />
      <path d="M12 14v3" />
    </svg>
  )
}

interface ExerciseAccessNoticeProps {
  exercisePath: string
  headingId?: string
}

export function ExerciseAccessNotice({ exercisePath, headingId }: ExerciseAccessNoticeProps) {
  return (
    <div className="exercise-access-notice">
      <span className="exercise-access-icon"><ExerciseLockIcon /></span>
      <p className="eyebrow">Members-only exercise</p>
      <h2 id={headingId}>Sign in to practise</h2>
      <p>Create a free account or log in to unlock this exercise and the full practice catalog. Public samples are available without an account.</p>
      <div className="button-row">
        <Link className="button" to="/login" state={{ from: exercisePath }}>Log in</Link>
        <Link className="button secondary" to="/register" state={{ from: exercisePath }}>Create account</Link>
      </div>
    </div>
  )
}
