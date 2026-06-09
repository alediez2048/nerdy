// PJ-07 — Agent /converse client.
import { clearToken, getAuthTokenSync } from './auth'
import type {
  ConverseRequest,
  ConverseResponse,
  ProfileStatus,
} from '../types/agent'

const API_ORIGIN = import.meta.env.DEV ? 'http://localhost:8000' : ''
const BASE = `${API_ORIGIN}/api/agent`

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

export async function converse(body: ConverseRequest): Promise<ConverseResponse> {
  const resp = await fetch(`${BASE}/converse`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
  })
  return handle<ConverseResponse>(resp)
}

export async function fetchProfileStatus(): Promise<ProfileStatus> {
  const resp = await fetch(`${BASE}/profile-status`, { headers: headers() })
  return handle<ProfileStatus>(resp)
}
