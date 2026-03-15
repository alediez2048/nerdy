// PA-09: Session detail — 7-tab dashboard
import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { colors, font } from '../design/tokens'
import { getSession } from '../api/sessions'
import { StatusBadge } from '../components/Badge'
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

  const activeTab = (searchParams.get('tab') as TabKey) || 'overview'

  useEffect(() => {
    if (!sessionId) return
    getSession(sessionId)
      .then(setSession)
      .catch((e) => setError(e.message))
  }, [sessionId])

  if (error) {
    return (
      <div style={s.page}>
        <p style={{ color: colors.red }}>{error}</p>
        <a href="/sessions" style={{ color: colors.cyan }}>← Back to Sessions</a>
      </div>
    )
  }
  if (!session) {
    return <div style={s.page}><p style={{ color: colors.muted }}>Loading...</p></div>
  }

  const config = session.config || {}

  const setTab = (tab: TabKey) => {
    setSearchParams({ tab })
  }

  return (
    <div style={s.page}>
      {/* Breadcrumb */}
      <div style={s.breadcrumb}>
        <span onClick={() => navigate('/sessions')} style={s.breadcrumbLink}>Sessions</span>
        <span style={{ color: colors.muted }}> / </span>
        <span style={{ color: colors.white }}>{session.name || session.session_id}</span>
      </div>

      {/* Session header */}
      <div style={s.header}>
        <div>
          <h1 style={s.title}>{session.name || session.session_id}</h1>
          <div style={s.meta}>
            <StatusBadge status={session.status} />
            <span style={{ color: colors.muted, fontSize: '13px' }}>
              {new Date(session.created_at).toLocaleDateString()} · {(config.audience as string) || ''} · {(config.campaign_goal as string) || ''}
            </span>
          </div>
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
        {activeTab === 'curated' && <CuratedSet />}
        {activeTab === 'health' && <SystemHealth sessionId={sessionId!} />}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: colors.ink,
    fontFamily: font.family,
    padding: '32px 20px',
    maxWidth: '1000px',
    margin: '0 auto',
  },
  breadcrumb: { marginBottom: '16px', fontSize: '13px' },
  breadcrumbLink: { color: colors.cyan, cursor: 'pointer' },
  header: { marginBottom: '24px' },
  title: {
    fontSize: '28px', fontWeight: 700, margin: '0 0 8px',
    color: colors.white,
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
