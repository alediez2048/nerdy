// PA-09: Session detail — 7-tab dashboard
import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { colors, font, radii } from '../design/tokens'
import { getSession, updateSessionName } from '../api/sessions'
import { StatusBadge } from '../components/Badge'
import ShareButton from '../components/ShareButton'
import type { SessionDetail as SessionDetailType } from '../types/session'

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
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [session, setSession] = useState<SessionDetailType | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isEditingName, setIsEditingName] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [isSavingName, setIsSavingName] = useState(false)
  const [renameError, setRenameError] = useState<string | null>(null)

  const activeTab = (searchParams.get('tab') as TabKey) || 'overview'

  useEffect(() => {
    if (!sessionId) return
    getSession(sessionId)
      .then(setSession)
      .catch((e) => setError(e.message))
  }, [sessionId])

  useEffect(() => {
    if (session) {
      setDraftName(session.name || session.session_id)
    }
  }, [session])

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
        {/* Breadcrumb */}
        <div style={s.breadcrumb}>
          <span onClick={() => navigate('/sessions')} style={s.breadcrumbLink}>Sessions</span>
          <span style={{ color: colors.muted }}> / </span>
          <span style={{ color: colors.white }}>{session.name || session.session_id}</span>
        </div>

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
            <ShareButton sessionId={sessionId!} />
          </div>
        </div>

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
          {activeTab === 'overview' && <Overview sessionId={sessionId!} />}
          {activeTab === 'quality' && <Quality sessionId={sessionId!} />}
          {activeTab === 'ads' && <AdLibrary sessionId={sessionId!} />}
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
    padding: '84px 20px 32px',
  },
  breadcrumb: { marginBottom: '16px', fontSize: '13px' },
  breadcrumbLink: { color: colors.cyan, cursor: 'pointer' },
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
}
