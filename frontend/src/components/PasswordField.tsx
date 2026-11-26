import { useId, useState } from 'react'
import './PasswordField.css'

interface PasswordFieldProps {
  value: string
  onChange: (value: string) => void
  autoComplete: 'current-password' | 'new-password'
  minLength?: number
  showRequiredMark?: boolean
}

export function PasswordField({
  value,
  onChange,
  autoComplete,
  minLength,
  showRequiredMark = false,
}: PasswordFieldProps) {
  const id = useId()
  const [visible, setVisible] = useState(false)

  return (
    <div className="password-field">
      <label htmlFor={id}>
        <span>Password{showRequiredMark && <> <span className="required-mark" aria-hidden="true">*</span></>}</span>
      </label>
      <div className="password-control">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          minLength={minLength}
          maxLength={128}
          autoComplete={autoComplete}
          autoCapitalize="none"
          spellCheck={false}
          required
        />
        <button
          className="password-toggle"
          type="button"
          aria-controls={id}
          aria-label={visible ? 'Hide password' : 'Show password'}
          onClick={() => setVisible((shown) => !shown)}
        >
          {visible ? 'Hide' : 'Show'}
        </button>
      </div>
    </div>
  )
}
