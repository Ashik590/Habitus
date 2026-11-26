export type CefrLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2'

export interface Language {
  code: string
  name: string
  bengali_name: string
}

export interface User {
  user_id: string
  name: string
  username: string
  email: string | null
  is_active: boolean
  profile_picture_url: string | null
  native_language: Language
  target_language: Language
}

export interface RegistrationRequest {
  name: string
  username: string
  email?: string | null
  password: string
  native_language_code: string
  target_language_code: string
}

export interface AccessTokenResponse {
  access_token: string
  token_type: string
}

export interface ExerciseSummary {
  exercise_id: number
  level: CefrLevel
  time_limit_seconds: number
  is_public: boolean
  is_locked: boolean
  completed: boolean
  overall_score: number | null
}

export interface Exercise extends ExerciseSummary {
  source_text: string
}

export interface ExerciseListResponse {
  items: ExerciseSummary[]
  total: number
  limit: number
  offset: number
}

export interface LevelStatistics {
  level: CefrLevel
  current_score: number | null
  exercises_completed: number
  exercises_available: number
}

export interface DimensionAverages {
  accuracy: number | null
  grammar: number | null
  naturalness: number | null
  fluency: number | null
}

export interface Statistics {
  source_language: string
  target_language: string
  exercises_completed: number
  level_scores: LevelStatistics[]
  dimension_averages: DimensionAverages
}

export interface EvaluationResponse {
  exercise_id: number
  is_valid_response: boolean
  recognized_translation: string
  accuracy_score: number
  grammar_score: number
  naturalness_score: number
  fluency_score: number
  overall_score: number
  feedback: string[]
  recommended_translations: string[]
  saved: boolean
}
