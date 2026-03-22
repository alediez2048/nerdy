// Ad-Ops-Autopilot — Dashboard API client

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
export const fetchSpc = (id: string) => get<Record<string, unknown>>(`${BASE}/${id}/spc`)
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
