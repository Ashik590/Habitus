import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import type { Language, LearningModule } from '../types/api'

const flags: Record<string, string> = { en: '🇬🇧', de: '🇩🇪', es: '🇪🇸' }

export function LanguagePage() {
  const { languageCode = 'en' } = useParams()
  const [languages, setLanguages] = useState<Language[]>([])
  const [modules, setModules] = useState<LearningModule[]>([])
  const [error, setError] = useState('')
  const language = useMemo(
    () => languages.find((item) => item.code === languageCode),
    [languageCode, languages],
  )

  useEffect(() => {
    Promise.all([api.getLanguages(), api.getModules()])
      .then(([languageItems, moduleItems]) => {
        setLanguages(languageItems)
        setModules(moduleItems)
      })
      .catch((requestError: unknown) => {
        setError(requestError instanceof Error ? requestError.message : 'Could not load this language.')
      })
  }, [])

  if (error) return <p className="status-message error">{error}</p>
  if (!language) return <p className="status-message">Loading language…</p>

  return (
    <section>
      <Link className="back-link" to="/languages">← All languages</Link>
      <div className="language-hero">
        <span className="language-flag large" aria-hidden="true">{flags[language.code] ?? '🌐'}</span>
        <div>
          <p className="eyebrow">{language.bengali_name}</p>
          <h1>Learn {language.name}</h1>
          <p>Choose a skill, work through level-based exercises, and build confidence through regular practice.</p>
        </div>
      </div>
      <div className="module-grid">
        {modules.map((module) => {
          const available = module.code === 'speaking'
          const card = (
            <article className={`module-card ${available ? '' : 'disabled'}`}>
              <div className="module-icon" aria-hidden="true">{module.code === 'speaking' ? '◉' : '▤'}</div>
              <span className="module-status">{available ? 'Available now' : 'Coming soon'}</span>
              <h2>{module.name}</h2>
              <p>{module.code === 'speaking' ? 'Translate Bengali prompts aloud and receive detailed AI feedback.' : 'Build comprehension with practical, level-based reading exercises.'}</p>
              {module.dimensions.length > 0 && (
                <div className="dimension-tags">
                  {module.dimensions.map((dimension) => <span key={dimension.code}>{dimension.name}</span>)}
                </div>
              )}
            </article>
          )
          return available ? (
            <Link className="module-link" key={module.code} to={`/languages/${language.code}/speaking/exercises`}>{card}</Link>
          ) : <div key={module.code}>{card}</div>
        })}
      </div>
    </section>
  )
}
