import { useEffect, useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import type { User } from '../types/api'
import { AuthContext } from './auth-context'

const REFRESH_TOKEN_KEY = 'habitus_refresh_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)

  useEffect(() => {
    const savedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
    if (!savedRefreshToken) {
      setIsInitializing(false)
      return
    }

    let cancelled = false

    api.refreshToken(savedRefreshToken)
      .then(async (tokens) => {
        if (cancelled) return
        localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
        const currentUser = await api.getCurrentUser(tokens.access_token)
        if (cancelled) return
        setAccessToken(tokens.access_token)
        setUser(currentUser)
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(REFRESH_TOKEN_KEY)
          setAccessToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsInitializing(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function login(email: string, password: string) {
    const tokens = await api.login(email, password)
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
    const currentUser = await api.getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(currentUser)
  }

  function logout() {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    setAccessToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ accessToken, user, isInitializing, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
