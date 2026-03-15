// Ad-Ops-Autopilot — SSE connection helper
import { getToken } from './auth'

export function createProgressStream(sessionId: string): EventSource {
  const token = getToken()
  const params = new URLSearchParams()
  if (token) params.set('token', token)

  const url = `/api/sessions/${sessionId}/progress${params.toString() ? '?' + params : ''}`
  return new EventSource(url)
}
