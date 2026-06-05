// BYO API keys client.

import type { Provider, UserKey, UserKeysResponse } from '../types/userKey'
import { clearToken, getAuthTokenSync } from './auth'

const API_ORIGIN = import.meta.env.DEV ? 'http://localhost:8000' : ''
const BASE = `${API_ORIGIN}/api/user/keys`

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = getAuthTokenSync()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
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

export async function listKeys(): Promise<UserKey[]> {
  const resp = await fetch(BASE, { headers: getHeaders() })
  const data = await handle<UserKeysResponse>(resp)
  return data.keys
}

export async function saveKey(provider: Provider, apiKey: string): Promise<UserKey> {
  const resp = await fetch(`${BASE}/${provider}`, {
    method: 'PUT',
    headers: getHeaders(),
    body: JSON.stringify({ api_key: apiKey }),
  })
  return handle<UserKey>(resp)
}

export async function deleteKey(provider: Provider): Promise<void> {
  const resp = await fetch(`${BASE}/${provider}`, {
    method: 'DELETE',
    headers: getHeaders(),
  })
  if (!resp.ok && resp.status !== 204) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
}
