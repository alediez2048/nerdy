// Auth (Clerk + legacy fallback)

// Clerk token getter — registered from App.tsx via useAuth()
let _clerkGetToken: (() => Promise<string | null>) | null = null
let _cachedClerkToken: string | null = null

/** Called once from App.tsx to register Clerk's getToken. */
export function registerClerkTokenGetter(fn: () => Promise<string | null>) {
  _clerkGetToken = fn
  // Refresh cached token periodically
  const refresh = () => fn().then((t) => { _cachedClerkToken = t })
  refresh()
  setInterval(refresh, 30_000) // refresh every 30s
}

/** Get auth token synchronously — uses cached Clerk token or localStorage. */
export function getAuthTokenSync(): string | null {
  return _cachedClerkToken || localStorage.getItem('token')
}

/** Get auth token — tries Clerk first, falls back to localStorage. */
export async function getAuthToken(): Promise<string | null> {
  if (_clerkGetToken) {
    const token = await _clerkGetToken()
    if (token) {
      _cachedClerkToken = token
      return token
    }
  }
  return localStorage.getItem('token')
}

/** Build headers with auth token (async — use in API calls). */
export async function getAuthHeaders(): Promise<HeadersInit> {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = await getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

// Legacy helpers (still used by some code paths)
export function getToken(): string | null {
  return localStorage.getItem('token')
}

export function saveToken(token: string) {
  localStorage.setItem('token', token)
}

export function clearToken() {
  localStorage.removeItem('token')
}

export function isLoggedIn(): boolean {
  return !!getToken()
}
