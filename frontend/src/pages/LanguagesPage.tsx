import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { api } from '../lib/api'
import type { Language } from '../types/api'

const flags: Record<string, string> = { bn: '🇧🇩', en: '🇬🇧', de: '🇩🇪', es: '🇪🇸' }

function languageOption(language: Language) {
  return `${flags[language.code] ?? '🌐'}  ${language.name}`
}

interface LanguagePickerProps {
  eyebrow: string
  title: string
  value: string
  languages: Language[]
  onChange: (code: string) => void
}

function LanguagePicker({ eyebrow, title, value, languages, onChange }: LanguagePickerProps) {
  return (
    <label className="practice-language-picker">
      <span className="picker-eyebrow">{eyebrow}</span>
      <strong>{title}</strong>
      <span className="picker-control">
        <select value={value} onChange={(event) => onChange(event.target.value)}>
          {languages.map((language) => (
            <option value={language.code} key={language.code}>
              {languageOption(language)}
            </option>
          ))}
        </select>
        <span className="picker-chevron" aria-hidden="true">⌄</span>
      </span>
    </label>
  )
}

export function LanguagesPage() {
  const navigate = useNavigate()
  const { user, isInitializing } = useAuth()
  const [languages, setLanguages] = useState<Language[]>([])
  const [guestSourceCode, setGuestSourceCode] = useState('bn')
  const [targetCode, setTargetCode] = useState('en')
  const [error, setError] = useState('')

  useEffect(() => {
    api.getLanguages().then(setLanguages).catch((requestError: unknown) => {
      setError(requestError instanceof Error ? requestError.message : 'Could not load languages.')
    })
  }, [])

  const sourceCode = user?.native_language.code ?? guestSourceCode
  const targetLanguages = useMemo(
    () => languages.filter((language) => language.code !== sourceCode),
    [languages, sourceCode],
  )
  const selectedTargetCode = targetLanguages.some((language) => language.code === targetCode)
    ? targetCode
    : targetLanguages[0]?.code ?? ''

  function beginPractice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!sourceCode || !selectedTargetCode || sourceCode === selectedTargetCode) return
    navigate(`/practice/${sourceCode}/${selectedTargetCode}/exercises`)
  }

  return (
    <section className="practice-setup-page">
      <div className="practice-setup-heading">
        <p className="eyebrow">Spoken translation practice</p>
        <h1>Choose your language direction</h1>
        <p>Translate prompts from a language you know into the language you want to speak naturally.</p>
      </div>

      {error && <p className="status-message error">{error}</p>}
      {!error && (languages.length === 0 || isInitializing) && (
        <p className="status-message">Loading languages…</p>
      )}

      {languages.length > 0 && !isInitializing && (
        <form className="practice-setup-panel" onSubmit={beginPractice}>
          {user ? (
            <div className="native-language-context">
              <span className="native-context-flag" aria-hidden="true">
                {flags[user.native_language.code] ?? '🌐'}
              </span>
              <span>
                Practising from <strong>{user.native_language.name}</strong>
              </span>
              <Link to="/profile">Change</Link>
            </div>
          ) : null}

          <div className={`practice-language-flow ${user ? 'authenticated' : ''}`}>
            {!user && (
              <LanguagePicker
                eyebrow="Source language"
                title="I already know"
                value={guestSourceCode}
                languages={languages}
                onChange={setGuestSourceCode}
              />
            )}

            {!user && <span className="language-flow-arrow" aria-hidden="true">→</span>}

            <LanguagePicker
              eyebrow="Target language"
              title="I want to practise"
              value={selectedTargetCode}
              languages={targetLanguages}
              onChange={setTargetCode}
            />
          </div>

          <div className="practice-setup-action">
            <button className="button" type="submit" disabled={targetLanguages.length === 0}>
              Browse exercises <span aria-hidden="true">→</span>
            </button>
            <small>Your progress is saved automatically when you are signed in.</small>
          </div>
        </form>
      )}
    </section>
  )
}
