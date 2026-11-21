import type { CefrLevel } from '../types/api'

interface ScoreBarProps {
  label: string
  score: number | null
  detail?: string
  tone?: 'rose' | 'green' | 'gold' | 'purple'
  level?: CefrLevel
}

export function ScoreBar({ label, score, detail, tone = 'rose', level }: ScoreBarProps) {
  const safeScore = score === null ? 0 : Math.min(100, Math.max(0, score))

  return (
    <div className={`score-bar-row${level ? ` score-bar-level level-${level.toLowerCase()}` : ''}`}>
      <div className="score-bar-meta">
        <span className={level ? 'level-badge' : undefined}>{label}</span>
        <span className="score-bar-value">
          {score === null ? 'Not started' : `${score.toFixed(1)}%`}
          {detail && <small>{detail}</small>}
        </span>
      </div>
      <div
        className="score-bar-track"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={score ?? 0}
      >
        <span className={`score-bar-fill ${tone}`} style={{ width: `${safeScore}%` }} />
      </div>
    </div>
  )
}
