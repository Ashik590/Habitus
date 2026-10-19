import { useEffect, useState } from 'react'
import { useAuth } from '../auth/useAuth'
import { ScoreBar } from '../components/ScoreBar'
import { api } from '../lib/api'
import type { Language, SpeakingStatistics } from '../types/api'

export function ProfilePage() {
  const { accessToken, user } = useAuth()
  const [languages, setLanguages] = useState<Language[]>([])
  const [languageCode, setLanguageCode] = useState('en')
  const [statistics, setStatistics] = useState<SpeakingStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!accessToken) return
    api.getStatistics(languageCode, accessToken)
      .then(setStatistics)
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Could not load statistics.')
      })
      .finally(() => setLoading(false))
  }, [accessToken, languageCode])

  const selectedLanguage = languages.find((language) => language.code === languageCode)

  function selectLanguage(code: string) {
    setLoading(true)
    setError('')
    setLanguageCode(code)
  }

  return (
    <section>
      <div className="profile-header">
        <div><p className="eyebrow">Learning dashboard</p><h1>{user?.name}</h1><p>See your current speaking performance based on the latest score for every completed exercise.</p></div>
        <label className="language-select">Language<select value={languageCode} onChange={(event) => selectLanguage(event.target.value)}>{languages.map((language) => <option value={language.code} key={language.code}>{language.name}</option>)}</select></label>
      </div>
      {error && <p className="status-message error">{error}</p>}
      {loading && !error && <p className="status-message">Loading your progress…</p>}
      {!loading && statistics && <div className="dashboard-grid">
        <article className="chart-card level-chart-card">
          <div className="chart-heading"><div><p className="eyebrow">Current score</p><h2>Performance by level</h2></div><div className="summary-number"><strong>{statistics.exercises_completed}</strong><span>exercises completed</span></div></div>
          <div className="bar-chart">
            {statistics.level_scores.map((level, index) => (
              <ScoreBar
                key={level.level}
                label={level.level}
                score={level.current_score}
                detail={`${level.exercises_completed} of ${level.exercises_available} completed`}
                tone={index >= 4 ? 'purple' : index >= 2 ? 'gold' : 'green'}
              />
            ))}
          </div>
        </article>
        <article className="chart-card dimension-chart-card">
          <div className="chart-heading"><div><p className="eyebrow">All levels combined</p><h2>Speaking metrics</h2></div><span className="language-pill">{selectedLanguage?.name ?? languageCode.toUpperCase()}</span></div>
          <div className="bar-chart">
            <ScoreBar label="Accuracy" score={statistics.dimension_averages.accuracy} />
            <ScoreBar label="Completeness" score={statistics.dimension_averages.completeness} />
            <ScoreBar label="Grammar" score={statistics.dimension_averages.grammar} tone="gold" />
            <ScoreBar label="Naturalness" score={statistics.dimension_averages.naturalness} tone="gold" />
            <ScoreBar label="Fluency" score={statistics.dimension_averages.fluency} tone="purple" />
          </div>
        </article>
      </div>}
    </section>
  )
}
