// PA-06: Session list — home screen
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'
import { listSessions, deleteSession } from '../api/sessions'
import SessionCard from '../components/SessionCard'
import SessionFilters, { type Filters } from '../components/SessionFilters'
import type { SessionSummary } from '../types/session'

const PAGE_SIZE = 20
const POLL_INTERVAL = 30_000

export default function SessionList() {
  const navigate = useNavigate()
  const isMobile = useMediaQuery('(max-width: 767px)')
  const isTablet = useMediaQuery('(max-width: 1024px)')
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [showHowItWorks, setShowHowItWorks] = useState(false)
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

  return (
    <div style={s.pageBg}>
      <div style={{ ...s.container, padding: isMobile ? '88px 16px 24px' : s.container.padding }}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.headerTop}>
            <div>
              <h1 style={{ ...s.title, fontSize: isMobile ? '24px' : s.title.fontSize }}>Sessions</h1>
              <p style={s.description}>
                Every session is a pipeline run. Use this view to scan recent work, spot runs that need attention,
                and jump into completed dashboards or live sessions faster.
              </p>
            </div>
            <div style={{ ...s.headerActions, width: isMobile ? '100%' : undefined }}>
              <button
                onClick={() => navigate('/sessions/new')}
                style={{ ...s.newBtn, width: isMobile ? '100%' : undefined }}
              >
                + New Session
              </button>
            </div>
          </div>

        </div>

        {/* How It Works toggle */}
        <button
          onClick={() => setShowHowItWorks(!showHowItWorks)}
          style={s.howToggle}
        >
          {showHowItWorks ? '▼' : '▶'} How the pipeline works
        </button>

        {showHowItWorks && (
          <div style={{ ...s.howPanel, padding: isMobile ? '20px 18px' : s.howPanel.padding }}>
            <div style={s.howSteps}>
              <div style={s.howStep}>
                <span style={s.howNum}>1</span>
                <div>
                  <strong style={{ color: colors.white }}>Brief Expansion</strong>
                  <p style={s.howText}>
                    Your session config (audience, persona, key message) is expanded into a full creative brief using
                    Gemini Flash. Brand knowledge, competitive landscape context, and audience pain points are injected
                    automatically from the knowledge base.
                  </p>
                </div>
              </div>
              <div style={s.howStep}>
                <span style={s.howNum}>2</span>
                <div>
                  <strong style={{ color: colors.white }}>Ad Copy Generation</strong>
                  <p style={s.howText}>
                    Each ad is generated using the Reference-Decompose-Recombine approach. Structural atoms (hook type,
                    body pattern, CTA style) are selected from the competitive pattern database and recombined with
                    the Varsity Tutors brand voice. Each ad gets a deterministic seed for reproducibility.
                  </p>
                </div>
              </div>
              <div style={s.howStep}>
                <span style={s.howNum}>3</span>
                <div>
                  <strong style={{ color: colors.white }}>5-Dimension Evaluation</strong>
                  <p style={s.howText}>
                    Every ad is scored across Clarity, Value Proposition, CTA, Brand Voice, and Emotional Resonance
                    using chain-of-thought evaluation. Each dimension gets a contrastive rationale explaining the score.
                    Ads scoring 7.0+ are published; below 5.5 are discarded; 5.5–7.0 enter regeneration.
                  </p>
                </div>
              </div>
              <div style={s.howStep}>
                <span style={s.howNum}>4</span>
                <div>
                  <strong style={{ color: colors.white }}>Image / Video Generation</strong>
                  <p style={s.howText}>
                    For image sessions, 3 image variants are generated per ad using the shared semantic brief, then
                    evaluated for visual attributes and text-image coherence. For video sessions, UGC-style video
                    variants are generated via Fal.ai using the 8-part prompt framework.
                  </p>
                </div>
              </div>
              <div style={s.howStep}>
                <span style={s.howNum}>5</span>
                <div>
                  <strong style={{ color: colors.white }}>Publish & Curate</strong>
                  <p style={s.howText}>
                    Ads that pass all quality gates are published to the session&apos;s ad library. From there, you can
                    browse results, add your best ads to the Curated Set for export, and download ZIP packages
                    ready for Meta Ads Manager.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

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
            <div
              style={{
                ...s.grid,
                gridTemplateColumns: isMobile
                  ? '1fr'
                  : isTablet
                    ? 'repeat(2, minmax(0, 1fr))'
                    : s.grid.gridTemplateColumns,
              }}
            >
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
  howToggle: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
    padding: '8px 0',
    marginBottom: '8px',
  },
  howPanel: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px 28px',
    marginBottom: '20px',
    borderLeft: `3px solid ${colors.cyan}`,
  },
  howSteps: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  },
  howStep: {
    display: 'flex',
    gap: '14px',
    alignItems: 'flex-start',
  },
  howNum: {
    width: '26px',
    height: '26px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '13px',
    flexShrink: 0,
    marginTop: '2px',
    fontFamily: font.family,
  },
  howText: {
    fontSize: '13px',
    color: colors.muted,
    margin: '4px 0 0',
    lineHeight: 1.5,
    fontFamily: font.family,
  },
  pageBg: {
    minHeight: '100vh',
    width: '100%',
    background: colors.ink,
    fontFamily: font.family,
  },
  container: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '96px 20px 32px', // Adjusted for NavBar (64px + 32px top padding)
  },
  header: {
    marginBottom: '24px',
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
