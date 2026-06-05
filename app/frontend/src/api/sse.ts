// SSE connection helper
import { getAuthToken, getAuthTokenSync } from './auth'

/**
 * Open a Server-Sent-Events stream for a session's progress.
 *
 * EventSource can't set request headers, so the auth token is passed as
 * a query parameter. Awaits the Clerk token before opening the
 * connection — on a fresh navigation the cached token may not be
 * populated yet, which caused the SSE to open without auth → 401 →
 * retries → user saw a stalled progress bar until manual refresh.
 *
 * Each call returns a fresh EventSource — callers should close the
 * previous one before opening a new one (e.g. for token rotation).
 */
export async function createProgressStream(sessionId: string): Promise<EventSource> {
  // Prefer cache hit (fast path on reconnects); fall back to async fetch.
  const token = getAuthTokenSync() || (await getAuthToken())
  const params = new URLSearchParams()
  if (token) params.set('token', token)

  const url = `/api/sessions/${sessionId}/progress${params.toString() ? '?' + params : ''}`
  return new EventSource(url)
}
