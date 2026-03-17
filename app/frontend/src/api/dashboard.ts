// Ad-Ops-Autopilot — Dashboard API client

const BASE = '/api/sessions'

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
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
export const fetchGlobalDashboard = () => get<Record<string, unknown>>('/api/dashboard/global')
