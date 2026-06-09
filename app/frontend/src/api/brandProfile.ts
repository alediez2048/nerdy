// PJ-08 — Current-user brand profile read client.
import { clearToken, getAuthTokenSync } from './auth'
import type { Phase } from '../types/agent'

const API_ORIGIN = import.meta.env.DEV ? 'http://localhost:8000' : ''
const BASE = `${API_ORIGIN}/api/me`

export interface BrandProfileFull {
  user_id: string
  business_name: string | null
  industry: string | null
  audience: string | null
  mission: string | null
  value_props: string[]
  tone_descriptors: string[]
  avoid_phrases: string[]
  do_dont_rules: { do: string[]; dont: string[] } | null
  palette_primary_hex: string | null
  palette_secondary_hex: string | null
  palette_accent_hex: string | null
  logo_asset_id: string | null
  logo_asset_url: string | null
  extras: Record<string, unknown>
  onboarding_phase: Phase
  good_enough_at: string | null
  created_at: string | null
  updated_at: string | null
}

function headers(): HeadersInit {
  const h: HeadersInit = { 'Content-Type': 'application/json' }
  const token = getAuthTokenSync()
  if (token) h['Authorization'] = `Bearer ${token}`
  return h
}

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    if (resp.status === 401) {
      clearToken()
      throw new Error('Session expired — please sign in again')
    }
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function getBrandProfile(): Promise<BrandProfileFull | null> {
  const resp = await fetch(`${BASE}/brand-profile`, { headers: headers() })
  if (resp.status === 404) return null
  return handle<BrandProfileFull>(resp)
}
