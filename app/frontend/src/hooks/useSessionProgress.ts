// PA-07: SSE hook for real-time session progress.
// Bugfix C (May 2026): refresh the Clerk JWT before each reconnect,
// and probe ``/api/auth/me`` after retries are exhausted so the user
// gets an auth-specific message instead of a generic "refresh" prompt
// when the real cause is an expired session token mid-stream.
import { useState, useEffect, useRef, useCallback } from 'react'
import { getAuthToken, getAuthTokenSync } from '../api/auth'
import { createProgressStream } from '../api/sse'
import type { ProgressEvent } from '../types/progress'

interface UseSessionProgressReturn {
  progress: ProgressEvent | null
  history: ProgressEvent[]
  connected: boolean
  error: string | null
}

const MAX_RETRIES = 3
const BASE_BACKOFF_MS = 1000

/**
 * Probe ``/api/auth/me`` to disambiguate "auth failed" from "network/server
 * error" after the EventSource gives up. EventSource hides the HTTP status,
 * so we have to ask a regular endpoint with the same credentials.
 */
async function probeAuthStatus(): Promise<'auth_failed' | 'ok' | 'unknown'> {
  try {
    const token = getAuthTokenSync()
    const resp = await fetch('/api/auth/me', {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (resp.status === 401 || resp.status === 403) return 'auth_failed'
    if (resp.ok) return 'ok'
    return 'unknown'
  } catch {
    return 'unknown'
  }
}

export default function useSessionProgress(
  sessionId: string,
): UseSessionProgressReturn {
  const [progress, setProgress] = useState<ProgressEvent | null>(null)
  const [history, setHistory] = useState<ProgressEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const retryCount = useRef(0)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
    }

    const source = createProgressStream(sessionId)
    sourceRef.current = source

    source.addEventListener('progress', (e: MessageEvent) => {
      try {
        const event: ProgressEvent = JSON.parse(e.data)
        setProgress(event)
        setHistory((prev) => [...prev, event])
        retryCount.current = 0 // Reset on successful message

        // Stop listening on completion or error
        if (
          event.type === 'pipeline_complete' ||
          event.type === 'pipeline_error' ||
          event.type === 'video_pipeline_complete'
        ) {
          source.close()
          setConnected(false)
        }
      } catch {
        // Ignore malformed events
      }
    })

    source.addEventListener('heartbeat', () => {
      // Heartbeat received — connection is alive
      retryCount.current = 0
    })

    source.onopen = () => {
      setConnected(true)
      setError(null)
      retryCount.current = 0
    }

    source.onerror = async () => {
      source.close()
      setConnected(false)

      if (retryCount.current < MAX_RETRIES) {
        const delay = BASE_BACKOFF_MS * Math.pow(2, retryCount.current)
        retryCount.current += 1
        // Refresh the Clerk token before reconnecting — handles the
        // mid-stream expiry case. ``getAuthToken`` updates the cached
        // token; the next ``createProgressStream`` call will pick it up.
        try {
          await getAuthToken()
        } catch {
          // Ignore — reconnect will fail again and surface the right error.
        }
        setTimeout(connect, delay)
      } else {
        // Exhausted retries. Probe to find out *why* the connection
        // keeps failing so we can show a helpful message.
        const status = await probeAuthStatus()
        if (status === 'auth_failed') {
          setError('Session expired — please sign in again.')
        } else {
          setError('Connection lost. Please refresh.')
        }
      }
    }
  }, [sessionId])

  useEffect(() => {
    // Skip connection when sessionId is empty (session not running)
    if (!sessionId) return
    connect()
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close()
        sourceRef.current = null
      }
    }
  }, [connect, sessionId])

  return { progress, history, connected, error }
}
