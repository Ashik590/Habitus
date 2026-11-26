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

  async function login(username: string, password: string) {
    const tokens = await api.login(username, password)
    const currentUser = await api.getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(currentUser)
    return currentUser
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

  async function updateNativeLanguage(languageCode: string) {
    if (!accessToken || !user) throw new Error('Authentication is required.')
    // Swap the pair atomically if the new native language was the saved target.
    const targetCode = languageCode === user.target_language.code
      ? user.native_language.code
      : user.target_language.code
    const updatedUser = await api.updatePracticeLanguages(languageCode, targetCode, accessToken)
    setUser(updatedUser)
  }

  async function updateTargetLanguage(languageCode: string) {
    if (!accessToken || !user) throw new Error('Authentication is required.')
    const updatedUser = await api.updatePracticeLanguages(user.native_language.code, languageCode, accessToken)
    setUser(updatedUser)
  }

  async function updateProfilePicture(picture: File) {
    if (!accessToken) throw new Error('Authentication is required.')
    const updatedUser = await api.uploadProfilePicture(picture, accessToken)
    setUser(updatedUser)
  }

  async function removeProfilePicture() {
    if (!accessToken) throw new Error('Authentication is required.')
    const updatedUser = await api.removeProfilePicture(accessToken)
    setUser(updatedUser)
  }

  return (
    <AuthContext.Provider value={{
      accessToken,
      user,
      isAuthenticated,
      isInitializing,
      login,
      logout,
      updateNativeLanguage,
      updateTargetLanguage,
      updateProfilePicture,
      removeProfilePicture,
    }}>
      {children}
    </AuthContext.Provider>
  )
}
