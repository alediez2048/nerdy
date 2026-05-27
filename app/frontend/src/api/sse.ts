// SSE connection helper
import { getAuthTokenSync } from './auth'

/**
 * Open a Server-Sent-Events stream for a session's progress.
 *
 * EventSource can't set request headers, so the auth token is passed as
 * a query parameter. Bugfix C: switched from the legacy ``getToken``
 * (localStorage only) to ``getAuthTokenSync`` so Clerk-issued JWTs are
 * actually sent — the old helper returned ``null`` for Clerk users,
 * which only worked locally because dev mode skips JWT validation.
 *
 * Each call returns a fresh EventSource — callers should close the
 * previous one before opening a new one (e.g. for token rotation).
 */
export function createProgressStream(sessionId: string): EventSource {
  const token = getAuthTokenSync()
  const params = new URLSearchParams()
  if (token) params.set('token', token)

  const url = `/api/sessions/${sessionId}/progress${params.toString() ? '?' + params : ''}`
  return new EventSource(url)
}
