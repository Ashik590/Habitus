import type { CefrLevel, EvaluationResponse, Language, LearningModule, SpeakingExercise, SpeakingExerciseListResponse, SpeakingStatistics, TokenPair, User } from '../types/api'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}, accessToken?: string | null): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
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
  return response.json() as Promise<T>
}

export const api = {
  getLanguages: () => request<Language[]>('/languages'),
  getModules: () => request<LearningModule[]>('/modules'),
  register: (name: string, email: string, password: string) => request<User>('/auth/register', {
    method: 'POST', body: JSON.stringify({ name, email, password }),
  }),
  login: (email: string, password: string) => request<TokenPair>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  refreshToken: (refreshToken: string) => request<TokenPair>('/auth/refresh', {
    method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }),
  }),
  getCurrentUser: (token: string) => request<User>('/users/me', {}, token),
  getExercises: (languageCode: string, token?: string | null, level?: CefrLevel) => request<SpeakingExerciseListResponse>(
    `/languages/${languageCode}/speaking/exercises${level ? `?level=${level}` : ''}`, {}, token,
  ),
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
