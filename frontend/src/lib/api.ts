import type { AccessTokenResponse, CefrLevel, EvaluationResponse, Exercise, ExerciseListResponse, Language, Statistics, User } from '../types/api'

// Keep the frontend and API on the same site in development so SameSite cookies work.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export class ApiError extends Error {
  status: number
  retryAfterSeconds: number | null

  constructor(status: number, message: string, retryAfterSeconds: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.retryAfterSeconds = retryAfterSeconds
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
    const retryAfterHeader = response.headers.get('Retry-After')
    const parsedRetryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : Number.NaN
    throw new ApiError(
      response.status,
      message,
      Number.isFinite(parsedRetryAfter) ? parsedRetryAfter : null,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

let cachedLanguages: Promise<Language[]> | null = null

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
  register: (name: string, email: string, password: string, nativeLanguageCode: string) => request<User>('/auth/register', {
    method: 'POST', body: JSON.stringify({ name, email, password, native_language_code: nativeLanguageCode }),
  }),
  login: (email: string, password: string) => request<AccessTokenResponse>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  refreshToken: () => request<AccessTokenResponse>('/auth/refresh', {
    method: 'POST',
  }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  getCurrentUser: (token: string) => request<User>('/users/me', {}, token),
  updateNativeLanguage: (nativeLanguageCode: string, token: string) => request<User>('/users/me/native-language', {
    method: 'PATCH', body: JSON.stringify({ native_language_code: nativeLanguageCode }),
  }, token),
  getExercises: (
    sourceCode: string,
    targetCode: string,
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
    return request<ExerciseListResponse>(
      `/practice/${sourceCode}/${targetCode}/exercises${query}`,
      {},
      token,
    )
  },
  getExercise: (sourceCode: string, targetCode: string, id: string, token?: string | null) => request<Exercise>(`/practice/${sourceCode}/${targetCode}/exercises/${id}`, {}, token),
  getStatistics: (sourceCode: string, targetCode: string, token: string) => request<Statistics>(`/users/me/practice/${sourceCode}/${targetCode}/statistics`, {}, token),
  evaluateExercise: (
    sourceCode: string,
    targetCode: string,
    exerciseId: number,
    audio: Blob,
    feedbackLanguage: 'en' | 'bn',
    token?: string | null,
  ) => {
    const extension = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('mp4') ? 'm4a' : 'webm'
    const form = new FormData()
    form.append('audio', audio, `answer.${extension}`)
    form.append('feedback_language', feedbackLanguage)
    return request<EvaluationResponse>(`/practice/${sourceCode}/${targetCode}/exercises/${exerciseId}/evaluate`, {
      method: 'POST',
      body: form,
    }, token)
  },
}
