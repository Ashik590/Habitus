import { createContext } from 'react'
import type { User } from '../types/api'

export interface AuthContextValue {
  accessToken: string | null
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
