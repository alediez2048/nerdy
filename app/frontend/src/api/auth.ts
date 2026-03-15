// Ad-Ops-Autopilot — Auth API client

const BASE = '/api/auth'

export interface AuthUser {
  id: number
  email: string
  name: string
  picture_url: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export async function googleLogin(idToken: string): Promise<LoginResponse> {
  const resp = await fetch(`${BASE}/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({ detail: resp.statusText }))
    throw new Error(body.detail || `HTTP ${resp.status}`)
  }
  return resp.json()
}

export function saveToken(token: string) {
  localStorage.setItem('token', token)
}

export function getToken(): string | null {
  return localStorage.getItem('token')
}

export function clearToken() {
  localStorage.removeItem('token')
}

export function isLoggedIn(): boolean {
  return !!getToken()
}
