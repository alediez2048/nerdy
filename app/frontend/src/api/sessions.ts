// Ad-Ops-Autopilot — Session API client

import type {
  SessionCreate,
  SessionDetail,
  SessionListResponse,
} from '../types/session'

const BASE = '/api/sessions'

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export async function createSession(
  data: SessionCreate & { campaign_id?: string },
): Promise<SessionDetail> {
  const resp = await fetch(BASE, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<SessionDetail>(resp)
}

export async function listSessions(params?: {
  session_type?: string
  audience?: string
  campaign_goal?: string
  status?: string
  offset?: number
  limit?: number
}): Promise<SessionListResponse> {
  const query = new URLSearchParams()
  if (params?.session_type) query.set('session_type', params.session_type)
  if (params?.audience) query.set('audience', params.audience)
  if (params?.campaign_goal) query.set('campaign_goal', params.campaign_goal)
  if (params?.status) query.set('status', params.status)
  if (params?.offset !== undefined) query.set('offset', String(params.offset))
  if (params?.limit !== undefined) query.set('limit', String(params.limit))

  const url = query.toString() ? `${BASE}?${query}` : BASE
  const resp = await fetch(url, { headers: getHeaders() })
  return handleResponse<SessionListResponse>(resp)
}

export async function getSession(
  sessionId: string,
): Promise<SessionDetail> {
  const resp = await fetch(`${BASE}/${sessionId}`, { headers: getHeaders() })
  return handleResponse<SessionDetail>(resp)
}

export async function updateSessionName(
  sessionId: string,
  name: string,
): Promise<SessionDetail> {
  const resp = await fetch(`${BASE}/${sessionId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify({ name }),
  })
  return handleResponse<SessionDetail>(resp)
}

// PC-12: Update session (supports name and/or campaign_id)
export async function updateSession(
  sessionId: string,
  data: { name?: string; campaign_id?: string | null },
): Promise<SessionDetail> {
  const resp = await fetch(`${BASE}/${sessionId}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(data),
  })
  return handleResponse<SessionDetail>(resp)
}

export async function deleteSession(sessionId: string): Promise<void> {
  const resp = await fetch(`${BASE}/${sessionId}`, {
    method: 'DELETE',
    headers: getHeaders(),
  })
  if (!resp.ok && resp.status !== 204) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
}
