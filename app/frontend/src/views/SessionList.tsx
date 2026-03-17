// PA-06: Session list — home screen
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { listSessions, deleteSession } from '../api/sessions'
import SessionCard from '../components/SessionCard'
import SessionFilters, { type Filters } from '../components/SessionFilters'
import type { SessionSummary } from '../types/session'

const PAGE_SIZE = 20
const POLL_INTERVAL = 30_000

export default function SessionList() {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [filters, setFilters] = useState<Filters>({
    audience: '',
    campaign_goal: '',
    status: '',
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchSessions = useCallback(
    async (newOffset = 0, append = false) => {
      try {
        if (!append) setLoading(true)
        const res = await listSessions({
          audience: filters.audience || undefined,
          campaign_goal: filters.campaign_goal || undefined,
          status: filters.status || undefined,
          offset: newOffset,
          limit: PAGE_SIZE,
        })
        setSessions((prev) => (append ? [...prev, ...res.sessions] : res.sessions))
        setTotal(res.total)
        setOffset(newOffset)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions')
      } finally {
        setLoading(false)
      }
    },
    [filters],
  )

  // Initial fetch + refetch on filter change
  useEffect(() => {
    fetchSessions(0)
  }, [fetchSessions])

  // 30s polling for running sessions
  useEffect(() => {
    const hasRunning = sessions.some((s) => s.status === 'running')
    if (hasRunning) {
      pollRef.current = setInterval(() => fetchSessions(0), POLL_INTERVAL)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [sessions, fetchSessions])

  const handleDelete = async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      setTotal((prev) => prev - 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session')
    }
  }

  const hasMore = offset + PAGE_SIZE < total

  return (
    <div style={s.page}>
      <div style={s.container}>
        {/* Header */}
        <div style={s.header}>
          <h1 style={s.title}>Sessions</h1>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button onClick={() => navigate('/dashboard')} style={s.dashboardBtn}>
              Dashboard
            </button>
            <button onClick={() => navigate('/sessions/new')} style={s.newBtn}>
              + New Session
            </button>
          </div>
        </div>

        {/* Filters */}
        <SessionFilters filters={filters} onChange={setFilters} />

        {/* Error */}
        {error && <p style={s.error}>{error}</p>}

        {/* Session list */}
        {loading && sessions.length === 0 ? (
          <p style={s.empty}>Loading...</p>
        ) : sessions.length === 0 ? (
          <div style={s.emptyState}>
            <p style={s.emptyTitle}>No sessions yet</p>
            <p style={s.emptySubtitle}>
              Create your first session to start generating ads.
            </p>
            <button onClick={() => navigate('/sessions/new')} style={s.newBtn}>
              + Create Session
            </button>
          </div>
        ) : (
          <>
            <div style={s.grid}>
              {sessions.map((session) => (
                <SessionCard key={session.session_id} session={session} onDelete={handleDelete} />
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div style={s.loadMore}>
                <button
                  onClick={() => fetchSessions(offset + PAGE_SIZE, true)}
                  style={s.loadMoreBtn}
                >
                  Load more ({total - offset - PAGE_SIZE} remaining)
                </button>
              </div>
            )}

            <p style={s.count}>
              Showing {sessions.length} of {total} sessions
            </p>
          </>
        )}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: colors.ink,
    fontFamily: font.family,
    padding: '40px 20px',
  },
  container: {
    maxWidth: '900px',
    margin: '0 auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '24px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    margin: 0,
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  dashboardBtn: {
    padding: '10px 24px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}`,
    background: 'transparent',
    color: colors.cyan,
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  newBtn: {
    padding: '10px 24px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  grid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  error: { color: colors.red, fontSize: '14px' },
  empty: { color: colors.muted, textAlign: 'center', padding: '40px' },
  emptyState: {
    textAlign: 'center',
    padding: '60px 20px',
    background: colors.surface,
    borderRadius: radii.card,
  },
  emptyTitle: {
    fontSize: '20px',
    fontWeight: 600,
    color: colors.white,
    margin: '0 0 8px',
  },
  emptySubtitle: {
    fontSize: '14px',
    color: colors.muted,
    margin: '0 0 20px',
  },
  loadMore: { textAlign: 'center', marginTop: '16px' },
  loadMoreBtn: {
    padding: '8px 20px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '13px',
    fontFamily: font.family,
  },
  count: {
    textAlign: 'center',
    color: colors.muted,
    fontSize: '12px',
    marginTop: '12px',
  },
}
