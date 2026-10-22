import type { AccessTokenResponse, CefrLevel, EvaluationResponse, Language, LearningModule, SpeakingExercise, SpeakingExerciseListResponse, SpeakingStatistics, User } from '../types/api'

// Keep the frontend and API on the same site in development so SameSite cookies work.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RefreshHandler = () => Promise<string | null>

let refreshHandler: RefreshHandler | null = null
let activeRefresh: Promise<string | null> | null = null

export function setRefreshHandler(handler: RefreshHandler | null) {
  refreshHandler = handler
}

async function refreshAccessToken() {
  if (!refreshHandler) return null
  if (!activeRefresh) {
    activeRefresh = refreshHandler().finally(() => {
      activeRefresh = null
    })
  }
  return activeRefresh
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string | null,
  hasRetried = false,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (response.status === 401 && accessToken && !hasRetried) {
    const renewedToken = await refreshAccessToken()
    if (renewedToken) return request<T>(path, options, renewedToken, true)
  }

  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // The server did not return a JSON error body.
    }
    throw new ApiError(response.status, message)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

let cachedLanguages: Promise<Language[]> | null = null
let cachedModules: Promise<LearningModule[]> | null = null

export const api = {
  getLanguages: () => {
    if (!cachedLanguages) {
      cachedLanguages = request<Language[]>('/languages').catch((err) => {
        cachedLanguages = null
        throw err
      })
    }
    return cachedLanguages
  },
  getModules: () => {
    if (!cachedModules) {
      cachedModules = request<LearningModule[]>('/modules').catch((err) => {
        cachedModules = null
        throw err
      })
    }
    return cachedModules
  },
  register: (name: string, email: string, password: string) => request<User>('/auth/register', {
    method: 'POST', body: JSON.stringify({ name, email, password }),
  }),
  login: (email: string, password: string) => request<AccessTokenResponse>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  refreshToken: () => request<AccessTokenResponse>('/auth/refresh', {
    method: 'POST',
  }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  getCurrentUser: (token: string) => request<User>('/users/me', {}, token),
  getExercises: (
    languageCode: string,
    token?: string | null,
    level?: CefrLevel,
    offset = 0,
    limit = 20,
  ) => {
    const params = new URLSearchParams()
    if (level) params.append('level', level)
    if (offset > 0) params.append('offset', String(offset))
    if (limit !== 20) params.append('limit', String(limit))
    const query = params.toString() ? `?${params.toString()}` : ''
    return request<SpeakingExerciseListResponse>(
      `/languages/${languageCode}/speaking/exercises${query}`,
      {},
      token,
    )
  },
  getExercise: (languageCode: string, id: string, token?: string | null) => request<SpeakingExercise>(`/languages/${languageCode}/speaking/exercises/${id}`, {}, token),
  getStatistics: (languageCode: string, token: string) => request<SpeakingStatistics>(`/users/me/languages/${languageCode}/speaking/statistics`, {}, token),
  evaluateExercise: (
    languageCode: string,
    exerciseId: number,
    audio: Blob,
    feedbackLanguage: 'en' | 'bn',
    token?: string | null,
  ) => {
    const extension = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('mp4') ? 'm4a' : 'webm'
    const form = new FormData()
    form.append('audio', audio, `answer.${extension}`)
    form.append('feedback_language', feedbackLanguage)
    return request<EvaluationResponse>(`/languages/${languageCode}/speaking/exercises/${exerciseId}/evaluate`, {
      method: 'POST',
      body: form,
    }, token)
  },
}
