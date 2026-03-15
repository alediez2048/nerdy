// Ad-Ops-Autopilot — Curation API client

const BASE = '/api/sessions'

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export interface CuratedAd {
  id: number
  ad_id: string
  position: number
  annotation: string | null
  edited_copy: Record<string, unknown> | null
  created_at: string
}

export interface CuratedSetData {
  id: number
  session_id: number
  name: string
  ads: CuratedAd[]
}

export async function getCuratedSet(sessionId: string): Promise<CuratedSetData | null> {
  const resp = await fetch(`${BASE}/${sessionId}/curated`, { headers: getHeaders() })
  if (resp.status === 404) return null
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function createCuratedSet(sessionId: string): Promise<CuratedSetData> {
  const resp = await fetch(`${BASE}/${sessionId}/curated`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ name: 'Default Set' }),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function addAdToCurated(sessionId: string, adId: string, position: number) {
  const resp = await fetch(`${BASE}/${sessionId}/curated/ads`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ ad_id: adId, position }),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function removeAdFromCurated(sessionId: string, adId: string) {
  const resp = await fetch(`${BASE}/${sessionId}/curated/ads/${adId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  })
  if (!resp.ok && resp.status !== 204) throw new Error(`HTTP ${resp.status}`)
}

export async function updateCuratedAd(
  sessionId: string,
  adId: string,
  update: { position?: number; annotation?: string; edited_copy?: Record<string, unknown> },
) {
  const resp = await fetch(`${BASE}/${sessionId}/curated/ads/${adId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(update),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.json()
}

export async function batchReorder(sessionId: string, adIds: string[]) {
  const resp = await fetch(`${BASE}/${sessionId}/curated/reorder`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ ad_ids: adIds }),
  })
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
}

export function getExportUrl(sessionId: string): string {
  const token = localStorage.getItem('token')
  return `${BASE}/${sessionId}/curated/export${token ? '?token=' + token : ''}`
}
