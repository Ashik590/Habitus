import { useState, type ReactNode } from 'react'
import { api } from '../lib/api'
import type { User } from '../types/api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)

  async function login(email: string, password: string) {
    const tokens = await api.login(email, password)
    const currentUser = await api.getCurrentUser(tokens.access_token)
    setAccessToken(tokens.access_token)
    setUser(currentUser)
  }

  function logout() {
    setAccessToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ accessToken, user, login, logout }}>{children}</AuthContext.Provider>
}
