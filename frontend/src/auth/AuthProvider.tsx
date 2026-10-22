import { useEffect, useState, type ReactNode } from 'react'
import { api, setRefreshHandler } from '../lib/api'
import type { User } from '../types/api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [isInitializing, setIsInitializing] = useState(true)
  const isAuthenticated = Boolean(user)

  useEffect(() => {
    let cancelled = false

    // Remove values left by versions that stored authentication in localStorage.
    localStorage.removeItem('habitus_refresh_token')
    localStorage.removeItem('habitus_user')

    api.refreshToken()
      .then(async (tokens) => {
        if (cancelled) return
        const currentUser = await api.getCurrentUser(tokens.access_token)
        if (cancelled) return
        setAccessToken(tokens.access_token)
        setUser(currentUser)
      })
      .catch(() => {
        if (!cancelled) {
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

  useEffect(() => {
    setRefreshHandler(async () => {
      try {
        const tokens = await api.refreshToken()
        setAccessToken(tokens.access_token)
        return tokens.access_token
      } catch {
        setAccessToken(null)
        setUser(null)
        return null
      }
    })

    return () => setRefreshHandler(null)
  }, [])

  async function login(email: string, password: string) {
    const tokens = await api.login(email, password)
    const currentUser = await api.getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(currentUser)
  }

  async function logout() {
    setAccessToken(null)
    setUser(null)
    try {
      await api.logout()
    } catch {
      // The local session is still cleared if the server is temporarily unavailable.
    }
  }

  return (
    <AuthContext.Provider value={{ accessToken, user, isAuthenticated, isInitializing, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
