// PA-07: SSE hook for real-time session progress
import { useState, useEffect, useRef, useCallback } from 'react'
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
          event.type === 'pipeline_error'
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

    source.onerror = () => {
      source.close()
      setConnected(false)

      if (retryCount.current < MAX_RETRIES) {
        const delay = BASE_BACKOFF_MS * Math.pow(2, retryCount.current)
        retryCount.current += 1
        setTimeout(connect, delay)
      } else {
        setError('Connection lost. Please refresh.')
      }
    }
  }, [sessionId])

  useEffect(() => {
    connect()
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close()
        sourceRef.current = null
      }
    }
  }, [connect])

  return { progress, history, connected, error }
}
