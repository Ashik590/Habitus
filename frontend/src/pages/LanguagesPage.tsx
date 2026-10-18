import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import type { Language } from '../types/api'

const flags: Record<string, string> = { en: '🇬🇧', de: '🇩🇪', es: '🇪🇸' }

export function LanguagesPage() {
  const [languages, setLanguages] = useState<Language[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : 'Could not load languages.')
    })
  }, [])

  return (
    <section>
      <div className="page-intro">
        <p className="eyebrow">Choose your target language</p>
        <h1>What do you want to speak?</h1>
        <p>Every language includes practical modules and CEFR-based exercises designed for Bengali-speaking learners.</p>
      </div>
      {error && <p className="status-message error">{error}</p>}
      {!error && languages.length === 0 && <p className="status-message">Loading languages…</p>}
      <div className="language-grid">
        {languages.map((language) => (
          <Link className="language-card" key={language.code} to={`/languages/${language.code}`}>
            <span className="language-flag" aria-hidden="true">{flags[language.code] ?? '🌐'}</span>
            <div>
              <span className="language-native">{language.bengali_name}</span>
              <h2>{language.name}</h2>
              <p>Speaking and reading practice from A1 to C1.</p>
            </div>
            <span className="card-arrow" aria-hidden="true">→</span>
          </Link>
        ))}
      </div>
    </section>
  )
}
