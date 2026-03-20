// PA-09: Session detail — 7-tab dashboard
// PC-12: Move to campaign functionality
import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { colors, font, radii } from '../design/tokens'
import { getSession, updateSessionName, updateSession } from '../api/sessions'
import { getCampaign, listCampaigns } from '../api/campaigns'
import { StatusBadge } from '../components/Badge'
import ShareButton from '../components/ShareButton'
import type { SessionDetail as SessionDetailType } from '../types/session'
import type { CampaignSummary } from '../types/campaign'

import Overview from '../tabs/Overview'
import Quality from '../tabs/Quality'
import AdLibrary from '../tabs/AdLibrary'
import CompetitiveIntel from '../tabs/CompetitiveIntel'
import TokenEconomics from '../tabs/TokenEconomics'
import CuratedSet from '../tabs/CuratedSet'
import SystemHealth from '../tabs/SystemHealth'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'quality', label: 'Quality' },
  { key: 'ads', label: 'Ad Library' },
  { key: 'competitive', label: 'Competitive' },
  { key: 'costs', label: 'Token Economics' },
  { key: 'curated', label: 'Curated Set' },
  { key: 'health', label: 'System Health' },
] as const

type TabKey = typeof TABS[number]['key']

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [session, setSession] = useState<SessionDetailType | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isEditingName, setIsEditingName] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [isSavingName, setIsSavingName] = useState(false)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [campaignName, setCampaignName] = useState<string | null>(null)
  // PC-12: Move to campaign
  const [showMoveModal, setShowMoveModal] = useState(false)
  const [availableCampaigns, setAvailableCampaigns] = useState<CampaignSummary[]>([])
  const [isMoving, setIsMoving] = useState(false)
  const [isLoadingCampaigns, setIsLoadingCampaigns] = useState(false)

  const activeTab = (searchParams.get('tab') as TabKey) || 'overview'

  useEffect(() => {
    if (!sessionId) return
    getSession(sessionId)
      .then((s) => {
        setSession(s)
        // Fetch campaign name if session belongs to a campaign
        if (s.campaign_id) {
          getCampaign(s.campaign_id)
            .then((c) => setCampaignName(c.name))
            .catch(() => {}) // Ignore campaign fetch errors
        }
      })
      .catch((e) => setError(e.message))
  }, [sessionId])

  useEffect(() => {
    if (session) {
      setDraftName(session.name || session.session_id)
    }
  }, [session])

  // PC-12: Load campaigns when move modal opens
  useEffect(() => {
    if (showMoveModal) {
      setIsLoadingCampaigns(true)
      listCampaigns({ status: 'active' })
        .then((res) => setAvailableCampaigns(res.campaigns))
        .catch(() => {})
        .finally(() => setIsLoadingCampaigns(false))
    }
  }, [showMoveModal])

  const handleMoveToCampaign = async (targetCampaignId: string | null) => {
    if (!sessionId) return
    try {
      setIsMoving(true)
      const updated = await updateSession(sessionId, { campaign_id: targetCampaignId })
      setSession(updated)
      if (updated.campaign_id) {
        const campaign = await getCampaign(updated.campaign_id)
        setCampaignName(campaign.name)
      } else {
        setCampaignName(null)
      }
      setShowMoveModal(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to move session')
    } finally {
      setIsMoving(false)
    }
  }

  if (error) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <p style={{ color: colors.red }}>{error}</p>
          <a href="/sessions" style={{ color: colors.cyan }}>← Back to Sessions</a>
        </div>
      </div>
    )
  }
  if (!session) {
    return <div style={s.pageBg}><div style={s.pageInner}><p style={{ color: colors.muted }}>Loading...</p></div></div>
  }

  const config = session.config || {}

  const setTab = (tab: TabKey) => {
    setSearchParams({ tab })
  }

  const handleSaveName = async () => {
    if (!sessionId) return
    const normalized = draftName.trim()
    if (!normalized) {
      setRenameError('Session name cannot be empty')
      return
    }
    try {
      setIsSavingName(true)
      setRenameError(null)
      const updated = await updateSessionName(sessionId, normalized)
      setSession(updated)
      setIsEditingName(false)
    } catch (e) {
      setRenameError(e instanceof Error ? e.message : 'Failed to rename session')
    } finally {
      setIsSavingName(false)
    }
  }

  const handleCancelName = () => {
    setDraftName(session.name || session.session_id)
    setRenameError(null)
    setIsEditingName(false)
  }

  return (
    <div style={s.pageBg}>
      <div style={s.pageInner}>
        {/* Session header */}
        <div style={s.header}>
          <div style={{ flex: 1 }}>
            {isEditingName ? (
              <div style={s.renameRow}>
                <input
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  style={s.renameInput}
                  placeholder="Session name"
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
                <h1 style={s.title}>{session.name || session.session_id}</h1>
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
            <div style={s.meta}>
              <StatusBadge status={session.status} />
              <span style={{ color: colors.muted, fontSize: '13px' }}>
                {new Date(session.created_at).toLocaleDateString()} · {(config.audience as string) || ''} · {(config.campaign_goal as string) || ''}
              </span>
            </div>
          </div>
          <div style={s.headerActions}>
            {/* PC-12: Move to campaign button */}
            {session.status !== 'running' && (
              <button
                onClick={() => setShowMoveModal(true)}
                style={s.moveBtn}
                title="Move to Campaign"
              >
                {session.campaign_id ? 'Change Campaign' : 'Move to Campaign'}
              </button>
            )}
            <ShareButton sessionId={sessionId!} />
          </div>
        </div>

        {/* PC-12: Move to campaign modal */}
        {showMoveModal && (
          <div style={s.modalOverlay} onClick={() => setShowMoveModal(false)}>
            <div style={s.modal} onClick={(e) => e.stopPropagation()}>
              <h3 style={s.modalTitle}>Move Session to Campaign</h3>
              {isLoadingCampaigns ? (
                <p style={s.modalText}>Loading campaigns...</p>
              ) : availableCampaigns.length === 0 ? (
                <div style={s.modalText}>
                  <p>No campaigns available. Create one first.</p>
                  <button
                    onClick={() => {
                      setShowMoveModal(false)
                      window.location.href = '/campaigns/new'
                    }}
                    style={s.modalCreateBtn}
                  >
                    + Create Campaign
                  </button>
                </div>
              ) : (
                <>
                  <div style={s.campaignList}>
                    <button
                      onClick={() => handleMoveToCampaign(null)}
                      disabled={isMoving}
                      style={{
                        ...s.campaignOption,
                        ...(session.campaign_id === null ? s.campaignOptionActive : {}),
                      }}
                    >
                      <span style={s.campaignOptionName}>Remove from Campaign</span>
                    </button>
                    {availableCampaigns.map((camp) => (
                      <button
                        key={camp.campaign_id}
                        onClick={() => handleMoveToCampaign(camp.campaign_id)}
                        disabled={isMoving}
                        style={{
                          ...s.campaignOption,
                          ...(session.campaign_id === camp.campaign_id ? s.campaignOptionActive : {}),
                        }}
                      >
                        <span style={s.campaignOptionName}>{camp.name}</span>
                        {camp.session_count > 0 && (
                          <span style={s.campaignOptionCount}>
                            {camp.session_count} {camp.session_count === 1 ? 'session' : 'sessions'}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                  <div style={s.modalActions}>
                    <button
                      onClick={() => setShowMoveModal(false)}
                      style={s.modalCancelBtn}
                      disabled={isMoving}
                    >
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* Tab navigation */}
        <div style={s.tabBar}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key)}
              style={activeTab === tab.key ? s.tabActive : s.tab}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div style={s.tabContent}>
          {activeTab === 'overview' && <Overview sessionId={sessionId!} sessionType={(config.session_type as string) || 'image'} />}
          {activeTab === 'quality' && <Quality sessionId={sessionId!} />}
          {activeTab === 'ads' && <AdLibrary sessionId={sessionId!} sessionType={(config.session_type as string) || 'image'} />}
          {activeTab === 'competitive' && <CompetitiveIntel />}
          {activeTab === 'costs' && <TokenEconomics sessionId={sessionId!} />}
          {activeTab === 'curated' && <CuratedSet sessionId={sessionId!} />}
          {activeTab === 'health' && <SystemHealth sessionId={sessionId!} />}
        </div>
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
  headerActions: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: '12px',
    marginLeft: 'auto',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
    marginBottom: '8px',
  },
  title: {
    fontSize: '28px', fontWeight: 700, margin: '0 0 8px',
    color: colors.white,
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
    border: `1px solid ${colors.muted}30`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  renameError: {
    color: colors.red,
    fontSize: '12px',
    marginBottom: '8px',
  },
  meta: { display: 'flex', alignItems: 'center', gap: '12px' },
  tabBar: {
    display: 'flex', gap: '4px', marginBottom: '24px', overflowX: 'auto',
    borderBottom: `1px solid ${colors.muted}20`, paddingBottom: '0',
  },
  tab: {
    padding: '10px 16px', background: 'transparent', border: 'none',
    borderBottom: '2px solid transparent',
    color: colors.muted, cursor: 'pointer', fontSize: '13px', fontWeight: 500,
    fontFamily: font.family, whiteSpace: 'nowrap',
  },
  tabActive: {
    padding: '10px 16px', background: 'transparent', border: 'none',
    borderBottom: `2px solid ${colors.cyan}`,
    color: colors.cyan, cursor: 'pointer', fontSize: '13px', fontWeight: 600,
    fontFamily: font.family, whiteSpace: 'nowrap',
  },
  tabContent: { minHeight: '300px' },
  // PC-12: Move to campaign
  moveBtn: {
    padding: '8px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
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
    maxWidth: '500px',
    width: '90%',
    maxHeight: '80vh',
    overflowY: 'auto',
    border: `1px solid ${colors.muted}30`,
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.white,
    margin: '0 0 16px',
  },
  modalText: {
    fontSize: '14px',
    color: colors.muted,
    lineHeight: 1.6,
    margin: '0 0 20px',
  },
  campaignList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '20px',
    maxHeight: '300px',
    overflowY: 'auto',
  },
  campaignOption: {
    padding: '12px 16px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}30`,
    background: 'transparent',
    color: colors.white,
    cursor: 'pointer',
    fontSize: '14px',
    fontFamily: font.family,
    textAlign: 'left',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    transition: 'all 0.2s',
  },
  campaignOptionActive: {
    borderColor: colors.cyan,
    background: `${colors.cyan}14`,
  },
  campaignOptionName: {
    fontWeight: 600,
  },
  campaignOptionCount: {
    fontSize: '12px',
    color: colors.muted,
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
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
  modalCreateBtn: {
    padding: '10px 20px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '14px',
    cursor: 'pointer',
    fontFamily: font.family,
    marginTop: '12px',
  },
}
