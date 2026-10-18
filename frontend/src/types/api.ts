export type CefrLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1'

export interface Language {
  code: string
  name: string
  bengali_name: string
}

export interface Dimension {
  code: string
  name: string
  bengali_name: string
  display_order: number
}

export interface LearningModule {
  code: string
  name: string
  bengali_name: string
  dimensions: Dimension[]
}

export interface User {
  user_id: string
  name: string
  email: string
  is_active: boolean
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface SpeakingExercise {
  exercise_id: number
  level: CefrLevel
  bengali_text: string
  time_limit_seconds: number
  completed: boolean
  overall_score: number | null
}

export interface SpeakingExerciseListResponse {
  items: SpeakingExercise[]
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
  completeness: number | null
  grammar: number | null
  naturalness: number | null
  fluency: number | null
}

export interface SpeakingStatistics {
  language: string
  module: 'speaking'
  exercises_completed: number
  level_scores: LevelStatistics[]
  dimension_averages: DimensionAverages
}

export interface EvaluationResponse {
  exercise_id: number
  is_valid_response: boolean
  recognized_translation: string
  accuracy_score: number
  completeness_score: number
  grammar_score: number
  naturalness_score: number
  fluency_score: number
  overall_score: number
  feedback: string
  recommended_translations: string[]
  saved: boolean
}
