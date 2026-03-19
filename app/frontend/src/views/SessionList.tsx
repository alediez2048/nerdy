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
    session_type: '',
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
          session_type: filters.session_type || undefined,
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
  const runningCount = sessions.filter((session) => session.status === 'running').length
  const completedCount = sessions.filter((session) => session.status === 'completed').length
  const totalSessionCost = sessions.reduce((sum, session) => {
    const results = session.results_summary
    const completedCost = typeof results?.cost_so_far === 'number' ? results.cost_so_far : 0
    const liveCost = typeof session.progress_summary?.cost_so_far === 'number'
      ? session.progress_summary.cost_so_far
      : 0
    return sum + Math.max(completedCost, liveCost)
  }, 0)
  const stats = [
    { label: 'Loaded Sessions', value: sessions.length, tone: colors.white },
    { label: 'Running Now', value: runningCount, tone: colors.cyan },
    { label: 'Completed', value: completedCount, tone: colors.mint },
    { label: 'Total Session Cost', value: `$${totalSessionCost.toFixed(2)}`, tone: colors.yellow },
  ]

  return (
    <div style={s.pageBg}>
      <div style={s.container}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.headerTop}>
            <div>
              <div style={s.breadcrumb}>
                <span onClick={() => navigate('/dashboard')} style={s.breadcrumbLink}>Dashboard</span>
                <span style={{ color: colors.muted }}> / </span>
                <span style={{ color: colors.white }}>Sessions</span>
              </div>
              <h1 style={s.title}>Sessions</h1>
              <p style={s.description}>
                Every session is a pipeline run. Use this view to scan recent work, spot runs that need attention,
                and jump into completed dashboards or live sessions faster.
              </p>
            </div>
            <div style={s.headerActions}>
              <button onClick={() => navigate('/sessions/new')} style={s.newBtn}>
                + New Session
              </button>
            </div>
          </div>

          <div style={s.summaryGrid}>
            {stats.map((stat) => (
              <div key={stat.label} style={s.summaryCard}>
                <div style={{ ...s.summaryValue, color: stat.tone }}>{stat.value}</div>
                <div style={s.summaryLabel}>{stat.label}</div>
              </div>
            ))}
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
            <p style={s.count}>
              Showing {sessions.length} of {total} sessions
            </p>
            <div style={s.grid}>
              {sessions.map((session) => (
                <SessionCard
                  key={session.session_id}
                  session={session}
                  onDelete={handleDelete}
                />
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

          </>
        )}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  pageBg: {
    minHeight: '100vh',
    width: '100%',
    background: colors.ink,
    fontFamily: font.family,
  },
  container: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '84px 20px 32px',
  },
  header: {
    marginBottom: '24px',
  },
  breadcrumb: {
    marginBottom: '8px',
    fontSize: '13px',
  },
  breadcrumbLink: {
    color: colors.cyan,
    cursor: 'pointer',
  },
  headerTop: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '16px',
    flexWrap: 'wrap',
    marginBottom: '24px',
  },
  headerActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 4px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  description: {
    maxWidth: '720px',
    color: colors.muted,
    fontSize: '13px',
    lineHeight: '1.6',
    margin: '10px 0 0',
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
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
    gap: '12px',
    marginBottom: 0,
  },
  summaryCard: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '18px 16px',
    border: `1px solid ${colors.muted}18`,
  },
  summaryValue: {
    fontSize: '26px',
    fontWeight: 700,
    lineHeight: 1.1,
  },
  summaryLabel: {
    fontSize: '12px',
    color: colors.muted,
    marginTop: '8px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
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
    textAlign: 'left',
    color: colors.muted,
    fontSize: '13px',
    margin: '0 0 12px',
  },
}
