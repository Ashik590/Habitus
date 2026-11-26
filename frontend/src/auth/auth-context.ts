import { createContext } from 'react'
import type { User } from '../types/api'

export interface AuthContextValue {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  isInitializing: boolean
  login: (username: string, password: string) => Promise<User>
  logout: () => Promise<void>
  updateNativeLanguage: (languageCode: string) => Promise<void>
  updateTargetLanguage: (languageCode: string) => Promise<void>
  updateProfilePicture: (picture: File) => Promise<void>
  removeProfilePicture: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
