// Dashboard API client

import { getAuthTokenSync } from './auth'

const BASE = '/api/sessions'

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = getAuthTokenSync()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

async function get<T>(url: string): Promise<T> {
  const resp = await fetch(url, { headers: getHeaders() })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export const fetchSummary = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/summary`)
export const fetchCycles = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/cycles`)
export const fetchDimensions = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/dimensions`)
export const fetchCosts = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/costs`)
export const fetchAds = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/ads`)
export const fetchAdVariants = (sessionId: string, adId: string) =>
  get<AnyVariantsResponse>(`${BASE}/${sessionId}/ads/${adId}/variants`)
export const fetchSpc = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/spc`)

export interface AdVariant {
  variant_type: string
  image_path: string | null
  image_url: string | null
  model_used: string
  predicted_cost_usd: number
  attribute_pass_pct: number
  coherence_avg: number
  composite_score: number
  is_winner: boolean
  lost_by: {
    dimension: 'attribute' | 'coherence' | 'tie'
    own_score: number
    winner_score: number
    composite_delta: number
  } | null
}

export interface AdVariantsResponse {
  session_id: string
  ad_id: string
  schema_version?: 'v1'
  selection_criteria: {
    formula: string
    winner_variant_type: string
    winner_composite_score: number
  }
  variants: AdVariant[]
}

// PI-08: v2 shape — per-dimension scores + winner_reason + rejection_reason.
export interface DimensionScore {
  score: number
  weight: number
  rationale: string
}
export interface GateEvaluation {
  triggered: boolean
  rationale: string
}
export interface AdVariantV2 {
  variant_type: string
  media_type: 'image' | 'video'
  image_path: string | null
  image_url: string | null
  model_used: string
  predicted_cost_usd: number
  composite_score: number
  raw_score: number
  penalty_multiplier: number
  dimensions: Record<string, DimensionScore>
  penalty_gates: Record<string, GateEvaluation>
  is_winner: boolean
  rejection_reason?: {
    composite_delta: number
    worst_dimension: string
    worst_dimension_delta: number
    worst_dimension_rationale: string
  }
}

export interface AdVariantsV2Response {
  session_id: string
  ad_id: string
  schema_version: 'v2'
  selection_criteria: {
    formula: string
    winner_variant_type: string
    winner_composite_score: number
  }
  winner_reason: {
    composite_score: number
    distinguishing_dimensions: Array<{
      dimension: string
      delta_vs_mean?: number
      absolute_score?: number
      note?: string
    }>
  } | null
  variants: AdVariantV2[]
}

export type AnyVariantsResponse = AdVariantsResponse | AdVariantsV2Response
export const fetchCompetitive = () => get<Record<string, unknown>>('/api/competitive/summary')
export const fetchGlobalDashboard = (timeframe: 'all' | 'day' | 'month' | 'year' = 'all') =>
  get<Record<string, unknown>>(`/api/dashboard/global?timeframe=${timeframe}`)

export async function fetchCompetitiveAds(params?: {
  competitor?: string
  hook_type?: string
  offset?: number
  limit?: number
}): Promise<Record<string, unknown>> {
  const query = new URLSearchParams()
  if (params?.competitor) query.set('competitor', params.competitor)
  if (params?.hook_type) query.set('hook_type', params.hook_type)
  if (params?.offset) query.set('offset', String(params.offset))
  if (params?.limit) query.set('limit', String(params.limit))
  const qs = query.toString()
  return get(`/api/competitive/ads${qs ? '?' + qs : ''}`)
}
