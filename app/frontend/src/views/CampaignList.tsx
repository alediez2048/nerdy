// PC-06: Campaign list — campaigns home screen
import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'
import { listCampaigns } from '../api/campaigns'
import CampaignCard from '../components/CampaignCard'
import type { CampaignSummary } from '../types/campaign'

const PAGE_SIZE = 20
const POLL_INTERVAL = 30_000

type StatusFilter = 'all' | 'active' | 'archived'

export default function CampaignList() {
  const navigate = useNavigate()
  const isMobile = useMediaQuery('(max-width: 767px)')
  const isTablet = useMediaQuery('(max-width: 1024px)')
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('active')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchCampaigns = useCallback(
    async (newOffset = 0, append = false) => {
      try {
        if (!append) setLoading(true)
        const res = await listCampaigns({
          status: statusFilter === 'all' ? undefined : statusFilter,
          offset: newOffset,
          limit: PAGE_SIZE,
        })
        setCampaigns((prev) => (append ? [...prev, ...res.campaigns] : res.campaigns))
        setTotal(res.total)
        setOffset(newOffset)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load campaigns')
      } finally {
        setLoading(false)
      }
    },
    [statusFilter],
  )

  // Initial fetch + refetch on filter change
  useEffect(() => {
    fetchCampaigns(0)
  }, [fetchCampaigns])

  // 30s polling for updates
  useEffect(() => {
    pollRef.current = setInterval(() => fetchCampaigns(0), POLL_INTERVAL)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [fetchCampaigns])

  const handleArchive = async () => {
    // Refetch to update the list after archive
    await fetchCampaigns(0)
  }

  const hasMore = offset + PAGE_SIZE < total
  const activeCount = campaigns.filter((c) => c.status === 'active').length
  const archivedCount = campaigns.filter((c) => c.status === 'archived').length
  const totalSessions = campaigns.reduce((sum, c) => sum + c.session_count, 0)

  const stats = [
    { label: 'Total Campaigns', value: campaigns.length, tone: colors.white },
    { label: 'Active', value: activeCount, tone: colors.cyan },
    { label: 'Archived', value: archivedCount, tone: colors.muted },
    { label: 'Total Sessions', value: totalSessions, tone: colors.mint },
  ]

  return (
    <div style={s.pageBg}>
      <div style={{ ...s.container, padding: isMobile ? '88px 16px 24px' : s.container.padding }}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.headerTop}>
            <div>
              <h1 style={{ ...s.title, fontSize: isMobile ? '24px' : s.title.fontSize }}>Campaigns</h1>
              <p style={s.description}>
                Organize your sessions into campaigns. Each campaign can have default settings that
                pre-fill when creating new sessions.
              </p>
            </div>
            <div style={{ ...s.headerActions, width: isMobile ? '100%' : undefined }}>
              <button
                onClick={() => navigate('/campaigns/new')}
                style={{ ...s.newBtn, width: isMobile ? '100%' : undefined }}
              >
                + New Campaign
              </button>
            </div>
          </div>

          <div
            style={{
              ...s.summaryGrid,
              gridTemplateColumns: isMobile
                ? 'repeat(2, minmax(0, 1fr))'
                : isTablet
                  ? 'repeat(2, minmax(0, 1fr))'
                  : s.summaryGrid.gridTemplateColumns,
            }}
          >
            {stats.map((stat) => (
              <div key={stat.label} style={s.summaryCard}>
                <div style={{ ...s.summaryValue, color: stat.tone }}>{stat.value}</div>
                <div style={s.summaryLabel}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Status Filter */}
        <div style={s.filters}>
          <button
            onClick={() => setStatusFilter('all')}
            style={{
              ...s.filterBtn,
              ...(statusFilter === 'all' ? s.filterBtnActive : {}),
            }}
          >
            All
          </button>
          <button
            onClick={() => setStatusFilter('active')}
            style={{
              ...s.filterBtn,
              ...(statusFilter === 'active' ? s.filterBtnActive : {}),
            }}
          >
            Active
          </button>
          <button
            onClick={() => setStatusFilter('archived')}
            style={{
              ...s.filterBtn,
              ...(statusFilter === 'archived' ? s.filterBtnActive : {}),
            }}
          >
            Archived
          </button>
        </div>

        {/* Error */}
        {error && (
          <div style={s.error}>
            <p>{error}</p>
            <button onClick={() => fetchCampaigns(0)} style={s.retryBtn}>
              Retry
            </button>
          </div>
        )}

        {/* Campaign list */}
        {loading && campaigns.length === 0 ? (
          <p style={s.empty}>Loading...</p>
        ) : campaigns.length === 0 ? (
          <div style={s.emptyState}>
            <p style={s.emptyTitle}>No campaigns yet</p>
            <p style={s.emptySubtitle}>
              Create your first campaign to organize your ad sessions.
              <br />
              <span style={{ fontSize: '13px', color: colors.muted }}>
                Campaigns help you group related sessions and set default settings that pre-fill when creating new sessions.
              </span>
            </p>
            <button onClick={() => navigate('/campaigns/new')} style={s.newBtn}>
              + Create Campaign
            </button>
          </div>
        ) : (
          <>
            <p style={s.count}>
              Showing {campaigns.length} of {total} campaigns
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
              {campaigns.map((campaign) => (
                <CampaignCard
                  key={campaign.campaign_id}
                  campaign={campaign}
                  onArchive={handleArchive}
                />
              ))}
            </div>

            {/* Load more */}
            {hasMore && (
              <div style={s.loadMore}>
                <button
                  onClick={() => fetchCampaigns(offset + PAGE_SIZE, true)}
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
  headerActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
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
  filters: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
  },
  filterBtn: {
    padding: '8px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}30`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
  filterBtnActive: {
    borderColor: colors.cyan,
    background: `${colors.cyan}14`,
    color: colors.cyan,
  },
  error: { color: colors.red, fontSize: '14px' },
  count: {
    textAlign: 'left',
    color: colors.muted,
    fontSize: '13px',
    margin: '0 0 12px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: '12px',
  },
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
}
