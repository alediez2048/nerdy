// PC-08: Campaign detail — campaign info + session list
// PC-12: Archive confirmation, duplication, archived styling
import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { getCampaign, updateCampaign, getCampaignSessions, duplicateCampaign } from '../api/campaigns'
import { StatusBadge } from '../components/Badge'
import Badge from '../components/Badge'
import SessionCard from '../components/SessionCard'
import type { CampaignDetail as CampaignDetailType } from '../types/campaign'
import type { SessionSummary } from '../types/session'

const PAGE_SIZE = 20
const POLL_INTERVAL = 30_000

export default function CampaignDetail() {
  const { campaignId } = useParams<{ campaignId: string }>()
  const navigate = useNavigate()
  const [campaign, setCampaign] = useState<CampaignDetailType | null>(null)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [isEditingName, setIsEditingName] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [isSavingName, setIsSavingName] = useState(false)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [isTogglingArchive, setIsTogglingArchive] = useState(false)
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false)
  const [isDuplicating, setIsDuplicating] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchCampaign = useCallback(async () => {
    if (!campaignId) return
    try {
      const data = await getCampaign(campaignId)
      setCampaign(data)
      setDraftName(data.name)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load campaign')
    }
  }, [campaignId])

  const fetchSessions = useCallback(
    async (newOffset = 0, append = false) => {
      if (!campaignId) return
      try {
        const res = await getCampaignSessions(campaignId, {
          offset: newOffset,
          limit: PAGE_SIZE,
        })
        setSessions((prev) => (append ? [...prev, ...res.sessions] : res.sessions))
        setTotal(res.total)
        setOffset(newOffset)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load sessions')
      }
    },
    [campaignId],
  )

  useEffect(() => {
    fetchCampaign()
    fetchSessions(0)
  }, [fetchCampaign, fetchSessions])

  // Polling for running sessions
  useEffect(() => {
    const hasRunning = sessions.some((s) => s.status === 'running')
    if (hasRunning) {
      pollRef.current = setInterval(() => {
        fetchSessions(0)
      }, POLL_INTERVAL)
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [sessions, fetchSessions])

  const handleSaveName = async () => {
    if (!campaignId) return
    const normalized = draftName.trim()
    if (!normalized) {
      setRenameError('Campaign name cannot be empty')
      return
    }
    try {
      setIsSavingName(true)
      setRenameError(null)
      const updated = await updateCampaign(campaignId, { name: normalized })
      setCampaign(updated)
      setIsEditingName(false)
    } catch (e) {
      setRenameError(e instanceof Error ? e.message : 'Failed to rename campaign')
    } finally {
      setIsSavingName(false)
    }
  }

  const handleCancelName = () => {
    if (campaign) {
      setDraftName(campaign.name)
    }
    setRenameError(null)
    setIsEditingName(false)
  }

  const handleToggleArchive = async () => {
    if (!campaignId || !campaign) return
    
    // PC-12: Show confirmation for archiving (not unarchiving)
    if (campaign.status !== 'archived') {
      setShowArchiveConfirm(true)
      return
    }
    
    // Unarchive directly (no confirmation needed)
    try {
      setIsTogglingArchive(true)
      const updated = await updateCampaign(campaignId, { status: 'active' })
      setCampaign(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to unarchive campaign')
    } finally {
      setIsTogglingArchive(false)
    }
  }

  const handleConfirmArchive = async () => {
    if (!campaignId) return
    setShowArchiveConfirm(false)
    try {
      setIsTogglingArchive(true)
      const updated = await updateCampaign(campaignId, { status: 'archived' })
      setCampaign(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to archive campaign')
    } finally {
      setIsTogglingArchive(false)
    }
  }

  const handleDuplicate = async () => {
    if (!campaignId) return
    try {
      setIsDuplicating(true)
      const duplicated = await duplicateCampaign(campaignId)
      navigate(`/campaigns/${duplicated.campaign_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to duplicate campaign')
    } finally {
      setIsDuplicating(false)
    }
  }

  if (error && !campaign) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <p style={{ color: colors.red }}>{error}</p>
          <button onClick={() => navigate('/campaigns')} style={s.backLink}>
            ← Back to Campaigns
          </button>
        </div>
      </div>
    )
  }

  if (!campaign) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <p style={{ color: colors.muted }}>Loading...</p>
        </div>
      </div>
    )
  }

  const hasMore = offset + PAGE_SIZE < total

  return (
    <div style={s.pageBg}>
      <div style={s.pageInner}>
        {/* PC-12: Archived banner */}
        {campaign.status === 'archived' && (
          <div style={s.archivedBanner}>
            <span style={s.archivedBannerText}>This campaign is archived</span>
          </div>
        )}

        {/* Campaign header */}
        <div style={s.header}>
          <div style={{ flex: 1 }}>
            {isEditingName ? (
              <div style={s.renameRow}>
                <input
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveName()
                    if (e.key === 'Escape') handleCancelName()
                  }}
                  style={s.renameInput}
                  placeholder="Campaign name"
                  autoFocus
                />
                <button onClick={handleSaveName} style={s.renameSaveBtn} disabled={isSavingName}>
                  {isSavingName ? 'Saving...' : 'Save'}
                </button>
                <button onClick={handleCancelName} style={s.renameCancelBtn} disabled={isSavingName}>
                  Cancel
                </button>
              </div>
            ) : (
              <div style={s.titleRow}>
                <h1 style={s.title}>{campaign.name}</h1>
                <button
                  onClick={() => {
                    setIsEditingName(true)
                    setRenameError(null)
                  }}
                  style={s.renameBtn}
                >
                  Rename
                </button>
              </div>
            )}
            {renameError && <div style={s.renameError}>{renameError}</div>}

            {campaign.description && (
              <p style={s.description}>{campaign.description}</p>
            )}

            <div style={s.meta}>
              <StatusBadge status={campaign.status} />
              {campaign.audience && (
                <Badge
                  label={campaign.audience.charAt(0).toUpperCase() + campaign.audience.slice(1)}
                  color={colors.cyan}
                />
              )}
              {campaign.campaign_goal && (
                <Badge
                  label={campaign.campaign_goal.charAt(0).toUpperCase() + campaign.campaign_goal.slice(1)}
                  color={colors.mint}
                />
              )}
              <span style={{ color: colors.muted, fontSize: '13px' }}>
                {campaign.session_count} {campaign.session_count === 1 ? 'session' : 'sessions'} · Created {new Date(campaign.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>

        {/* Action bar */}
        <div style={s.actionBar}>
          <button
            onClick={() => navigate(`/campaigns/${campaignId}/sessions/new`)}
            style={s.newSessionBtn}
          >
            + New Session
          </button>
          <button
            onClick={handleDuplicate}
            disabled={isDuplicating}
            style={s.duplicateBtn}
          >
            {isDuplicating ? 'Duplicating...' : 'Duplicate'}
          </button>
          <button
            onClick={handleToggleArchive}
            disabled={isTogglingArchive}
            style={s.archiveBtn}
          >
            {isTogglingArchive
              ? 'Updating...'
              : campaign.status === 'archived'
                ? 'Unarchive'
                : 'Archive'}
          </button>
        </div>

        {/* PC-12: Archive confirmation dialog */}
        {showArchiveConfirm && (
          <div style={s.modalOverlay} onClick={() => setShowArchiveConfirm(false)}>
            <div style={s.modal} onClick={(e) => e.stopPropagation()}>
              <h3 style={s.modalTitle}>Archive Campaign?</h3>
              <p style={s.modalText}>
                Archive "{campaign.name}"? Sessions will not be deleted and will remain accessible.
              </p>
              <div style={s.modalActions}>
                <button onClick={handleConfirmArchive} style={s.modalConfirmBtn}>
                  Archive
                </button>
                <button onClick={() => setShowArchiveConfirm(false)} style={s.modalCancelBtn}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* PC-11: Stats panel */}
        {campaign.stats && (
          <div style={s.statsPanel}>
            <h2 style={s.statsTitle}>Campaign Statistics</h2>
            <div style={s.statsGrid}>
              <div style={s.statCard}>
                <div style={s.statValue}>{campaign.stats.total_sessions}</div>
                <div style={s.statLabel}>Total Sessions</div>
              </div>
              <div style={s.statCard}>
                <div style={s.statValue}>{campaign.stats.total_ads_generated}</div>
                <div style={s.statLabel}>Ads Generated</div>
              </div>
              <div style={s.statCard}>
                <div style={{ ...s.statValue, color: colors.mint }}>
                  {campaign.stats.total_ads_published}
                </div>
                <div style={s.statLabel}>Ads Published</div>
              </div>
              <div style={s.statCard}>
                <div style={{ ...s.statValue, color: colors.yellow }}>
                  {campaign.stats.avg_quality_score > 0 ? campaign.stats.avg_quality_score.toFixed(1) : '0.0'}
                </div>
                <div style={s.statLabel}>Avg Quality Score</div>
              </div>
              <div style={s.statCard}>
                <div style={{ ...s.statValue, color: colors.yellow }}>
                  ${campaign.stats.total_cost.toFixed(2)}
                </div>
                <div style={s.statLabel}>Total Cost</div>
              </div>
            </div>

            {/* Status breakdown */}
            {Object.keys(campaign.stats.sessions_by_status).length > 0 && (
              <div style={s.breakdown}>
                <div style={s.breakdownTitle}>Session Status</div>
                <div style={s.breakdownItems}>
                  {Object.entries(campaign.stats.sessions_by_status).map(([status, count]) => (
                    <div key={status} style={s.breakdownItem}>
                      <span style={s.breakdownLabel}>{status}</span>
                      <span style={s.breakdownValue}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Type breakdown */}
            {Object.keys(campaign.stats.session_types).length > 0 && (
              <div style={s.breakdown}>
                <div style={s.breakdownTitle}>Session Types</div>
                <div style={s.breakdownItems}>
                  {Object.entries(campaign.stats.session_types).map(([type, count]) => (
                    <div key={type} style={s.breakdownItem}>
                      <span style={s.breakdownLabel}>{type}</span>
                      <span style={s.breakdownValue}>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Session list */}
        {sessions.length === 0 ? (
          <div style={s.emptyState}>
            <p style={s.emptyTitle}>No sessions in this campaign yet</p>
            <p style={s.emptySubtitle}>
              Create your first session to start generating ads for this campaign.
              <br />
              <span style={{ fontSize: '13px', color: colors.muted }}>
                You can also move existing sessions here from the Sessions page.
              </span>
            </p>
            <div style={s.emptyActions}>
              <button
                onClick={() => navigate(`/campaigns/${campaignId}/sessions/new`)}
                style={s.newSessionBtn}
              >
                + Create Session
              </button>
              <button
                onClick={() => navigate('/sessions')}
                style={s.viewSessionsBtn}
              >
                View All Sessions
              </button>
            </div>
          </div>
        ) : (
          <>
            <p style={s.count}>
              Showing {sessions.length} of {total} sessions
            </p>
            <div style={s.grid}>
              {sessions.map((session) => (
                <SessionCard key={session.session_id} session={session} />
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
  pageInner: {
    maxWidth: '1000px',
    margin: '0 auto',
    padding: '96px 20px 32px', // Adjusted for NavBar (64px + 32px top padding)
  },
  header: {
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '16px',
    flexWrap: 'wrap',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
    marginBottom: '8px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 8px',
    color: colors.white,
  },
  description: {
    color: colors.muted,
    fontSize: '14px',
    lineHeight: 1.6,
    margin: '0 0 12px',
  },
  renameBtn: {
    padding: '6px 12px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}30`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  renameRow: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '8px',
  },
  renameInput: {
    minWidth: '260px',
    flex: 1,
    maxWidth: '420px',
    padding: '10px 14px',
    borderRadius: radii.input,
    border: `1px solid ${colors.cyan}40`,
    background: colors.ink,
    color: colors.white,
    fontSize: '14px',
    fontFamily: font.family,
    outline: 'none',
  },
  renameSaveBtn: {
    padding: '10px 14px',
    borderRadius: radii.button,
    border: 'none',
    background: `${colors.cyan}20`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
    fontFamily: font.family,
  },
  renameCancelBtn: {
    padding: '10px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  renameError: {
    color: colors.red,
    fontSize: '12px',
    marginTop: '4px',
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    marginTop: '8px',
  },
  actionBar: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px',
    flexWrap: 'wrap',
  },
  newSessionBtn: {
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
  archiveBtn: {
    padding: '10px 24px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
  },
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
    marginBottom: '24px',
  },
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
  backLink: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
    marginTop: '12px',
    padding: 0,
  },
  // PC-11: Stats panel
  statsPanel: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px',
    marginBottom: '32px',
  },
  statsTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.white,
    margin: '0 0 20px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  statCard: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  statValue: {
    fontSize: '24px',
    fontWeight: 700,
    color: colors.white,
  },
  statLabel: {
    fontSize: '12px',
    color: colors.muted,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  breakdown: {
    marginTop: '20px',
    paddingTop: '20px',
    borderTop: `1px solid ${colors.muted}20`,
  },
  breakdownTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: colors.white,
    marginBottom: '12px',
  },
  breakdownItems: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap',
  },
  breakdownItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  breakdownLabel: {
    fontSize: '13px',
    color: colors.muted,
    textTransform: 'capitalize',
  },
  breakdownValue: {
    fontSize: '16px',
    fontWeight: 600,
    color: colors.white,
  },
  // PC-12: Archived banner
  archivedBanner: {
    background: `${colors.muted}20`,
    border: `1px solid ${colors.muted}40`,
    borderRadius: radii.input,
    padding: '12px 16px',
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
  },
  archivedBannerText: {
    fontSize: '14px',
    color: colors.muted,
    fontStyle: 'italic',
  },
  // PC-12: Duplicate button
  duplicateBtn: {
    padding: '10px 24px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}50`,
    background: `${colors.cyan}14`,
    color: colors.cyan,
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  // PC-12: Modal
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
  },
  modal: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px',
    maxWidth: '400px',
    width: '90%',
    border: `1px solid ${colors.muted}30`,
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.white,
    margin: '0 0 12px',
  },
  modalText: {
    fontSize: '14px',
    color: colors.muted,
    lineHeight: 1.6,
    margin: '0 0 20px',
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
  },
  modalConfirmBtn: {
    padding: '10px 20px',
    borderRadius: radii.button,
    border: 'none',
    background: colors.red,
    color: colors.white,
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  modalCancelBtn: {
    padding: '10px 20px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  // PC-12: Empty state improvements
  emptyActions: {
    display: 'flex',
    gap: '12px',
    marginTop: '16px',
    flexWrap: 'wrap',
  },
  viewSessionsBtn: {
    padding: '10px 24px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    fontWeight: 600,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
}
