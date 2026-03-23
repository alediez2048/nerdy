// Global Curated Set page — aggregated curated ads from all sessions
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { getCuratedSet, downloadExportZip, type CuratedAd, type CuratedSetData } from '../api/curation'
import { listSessions } from '../api/sessions'
import { fetchAds } from '../api/dashboard'
import Badge from '../components/Badge'
import type { SessionSummary } from '../types/session'

interface AdData {
  ad_id: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  image_url: string | null
  video_url?: string | null
  video_remote_url?: string | null
}

function getVideoSrc(ad: AdData | undefined): string | null {
  if (!ad) return null
  const url = ad.video_remote_url || ad.video_url
  if (!url) return null
  return url.startsWith('http') ? url : `/api${url}`
}

interface SessionGroup {
  session: SessionSummary
  curated: CuratedSetData
  adMap: Record<string, AdData>
}

export default function CuratedSetPage() {
  const [groups, setGroups] = useState<SessionGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exportingAll, setExportingAll] = useState(false)
  const [exportingSession, setExportingSession] = useState<string | null>(null)

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    setError(null)
    try {
      // Fetch all sessions (API limit is 100 per page)
      const allSessions: SessionSummary[] = []
      let offset = 0
      const pageSize = 100
      while (true) {
        const resp = await listSessions({ limit: pageSize, offset })
        allSessions.push(...resp.sessions)
        if (allSessions.length >= (resp.total || resp.sessions.length) || resp.sessions.length < pageSize) break
        offset += pageSize
      }
      const sessions = allSessions

      const results: SessionGroup[] = []

      await Promise.all(
        sessions.map(async (session) => {
          try {
            const curated = await getCuratedSet(session.session_id)
            if (!curated || curated.ads.length === 0) return

            const adsData = await fetchAds(session.session_id).catch(() => ({}))
            const lib = ((adsData as Record<string, unknown>).ad_library || []) as AdData[]
            const adMap: Record<string, AdData> = {}
            lib.forEach((a) => { adMap[a.ad_id] = a })

            results.push({ session, curated, adMap })
          } catch {
            // Skip sessions that fail
          }
        }),
      )

      // Sort by most recently created first
      results.sort((a, b) => {
        const dateA = new Date(a.session.created_at).getTime()
        const dateB = new Date(b.session.created_at).getTime()
        return dateB - dateA
      })

      setGroups(results)
    } catch (e) {
      setError(e instanceof Error ? e.message : typeof e === 'string' ? e : 'Failed to load sessions')
    }
    setLoading(false)
  }

  async function handleExportSession(sessionId: string) {
    setExportingSession(sessionId)
    try {
      await downloadExportZip(sessionId)
    } catch (e) {
      alert(`Export failed: ${e}`)
    }
    setExportingSession(null)
  }

  async function handleExportAll() {
    setExportingAll(true)
    for (const group of groups) {
      try {
        await downloadExportZip(group.session.session_id)
      } catch {
        // Continue with remaining sessions
      }
    }
    setExportingAll(false)
  }

  const totalAds = groups.reduce((sum, g) => sum + g.curated.ads.length, 0)

  if (loading) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <p style={{ color: colors.muted }}>Loading curated sets from all sessions...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={s.pageBg}>
        <div style={s.pageInner}>
          <p style={{ color: colors.red }}>{error}</p>
          <a href="/sessions" style={{ color: colors.cyan }}>Back to Sessions</a>
        </div>
      </div>
    )
  }

  return (
    <div style={s.pageBg}>
      <div style={s.pageInner}>
        {/* Header */}
        <div style={s.header}>
          <div>
            <h1 style={s.title}>Curated Set</h1>
            <p style={s.subtitle}>
              Hand-picked ads from all sessions, ready for export
            </p>
          </div>
          {groups.length > 0 && (
            <div style={s.headerActions}>
              <span style={s.totalBadge}>
                {totalAds} ad{totalAds !== 1 ? 's' : ''} across {groups.length} session{groups.length !== 1 ? 's' : ''}
              </span>
              <button
                onClick={handleExportAll}
                style={s.exportAllBtn}
                disabled={exportingAll}
              >
                {exportingAll ? 'Exporting...' : 'Export All'}
              </button>
            </div>
          )}
        </div>

        {groups.length === 0 ? (
          <div style={s.emptyWrap}>
            <div style={s.empty}>
              <h3 style={s.emptyTitle}>No Curated Ads Yet</h3>
              <p style={s.emptyText}>
                Open a session, browse the Ad Library tab, and add your best ads to a curated set.
                They will appear here once curated.
              </p>
              <a href="/sessions" style={s.linkBtn}>Browse Sessions</a>
            </div>
          </div>
        ) : (
          <div style={s.groupList}>
            {groups.map((group) => (
              <SessionGroupCard
                key={group.session.session_id}
                group={group}
                exporting={exportingSession === group.session.session_id}
                onExport={() => handleExportSession(group.session.session_id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SessionGroupCard({
  group,
  exporting,
  onExport,
}: {
  group: SessionGroup
  exporting: boolean
  onExport: () => void
}) {
  const { session, curated, adMap } = group

  return (
    <div style={s.groupCard}>
      {/* Session header */}
      <div style={s.groupHeader}>
        <div>
          <div style={s.sessionName}>
            Session: &ldquo;{session.name || 'Untitled'}&rdquo;
            <span style={s.sessionId}>({session.session_id})</span>
          </div>
          <div style={s.adCount}>
            {curated.ads.length} ad{curated.ads.length !== 1 ? 's' : ''} curated
          </div>
        </div>
        <button
          onClick={onExport}
          style={s.exportBtn}
          disabled={exporting}
        >
          {exporting ? 'Exporting...' : 'Export ZIP'}
        </button>
      </div>

      {/* Ad cards */}
      <div style={s.adList}>
        {curated.ads.map((cad, i) => (
          <AdCard key={cad.ad_id} cad={cad} ad={adMap[cad.ad_id]} index={i} />
        ))}
      </div>
    </div>
  )
}

function AdCard({
  cad,
  ad,
  index,
}: {
  cad: CuratedAd
  ad: AdData | undefined
  index: number
}) {
  return (
    <div style={s.card}>
      <div style={s.cardLayout}>
        {/* Media preview */}
        {getVideoSrc(ad) && (
          <video
            src={getVideoSrc(ad)!}
            controls
            muted
            playsInline
            style={s.cardMedia}
            onError={(e) => { (e.target as HTMLVideoElement).style.display = 'none' }}
          />
        )}
        {ad?.image_url && !getVideoSrc(ad) && (
          <img
            src={`/api${ad.image_url}`}
            alt={cad.ad_id}
            style={s.cardMedia}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
          />
        )}

        {/* Content */}
        <div style={s.cardBody}>
          <div style={s.cardHeader}>
            <div style={s.cardTitleRow}>
              <span style={s.position}>{index + 1}.</span>
              <span style={s.adId}>{cad.ad_id}</span>
              {ad && (
                <Badge
                  label={`Copy: ${ad.aggregate_score.toFixed(1)}`}
                  color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow}
                />
              )}
            </div>
          </div>

          <p style={s.copyPreview}>
            {ad?.copy?.primary_text || '---'}
          </p>

          {ad?.copy?.headline && (
            <p style={s.headline}>
              <strong>Headline:</strong> {ad.copy.headline}
            </p>
          )}

          {cad.annotation && (
            <p style={s.annotation}>
              Note: &ldquo;{cad.annotation}&rdquo;
            </p>
          )}
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
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '84px 20px 32px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
    flexWrap: 'wrap',
    gap: '16px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 700,
    margin: '0 0 4px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    fontFamily: font.family,
  },
  subtitle: {
    color: colors.muted,
    fontSize: '14px',
    margin: 0,
    fontFamily: font.family,
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  totalBadge: {
    fontSize: '13px',
    color: colors.muted,
    fontFamily: font.family,
  },
  exportAllBtn: {
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
  emptyWrap: {
    display: 'flex',
    justifyContent: 'center',
    padding: '40px 0',
  },
  empty: {
    textAlign: 'center',
    padding: '48px 32px',
    background: colors.surface,
    borderRadius: radii.card,
    maxWidth: '480px',
  },
  emptyTitle: {
    fontSize: '20px',
    fontWeight: 700,
    color: colors.white,
    margin: '0 0 8px',
    fontFamily: font.family,
  },
  emptyText: {
    fontSize: '14px',
    color: colors.muted,
    margin: '0 0 20px',
    lineHeight: 1.5,
    fontFamily: font.family,
  },
  linkBtn: {
    display: 'inline-block',
    padding: '10px 24px',
    borderRadius: radii.button,
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '14px',
    textDecoration: 'none',
    fontFamily: font.family,
  },
  groupList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  groupCard: {
    background: colors.surface,
    borderRadius: radii.card,
    overflow: 'hidden',
    fontFamily: font.family,
  },
  groupHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px 20px',
    borderBottom: `1px solid ${colors.muted}15`,
  },
  sessionName: {
    fontSize: '16px',
    fontWeight: 600,
    color: colors.white,
    fontFamily: font.family,
  },
  sessionId: {
    fontSize: '12px',
    color: colors.muted,
    fontWeight: 400,
    marginLeft: '8px',
  },
  adCount: {
    fontSize: '13px',
    color: colors.muted,
    marginTop: '4px',
    fontFamily: font.family,
  },
  exportBtn: {
    padding: '8px 20px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 600,
    fontSize: '13px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  adList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1px',
    background: `${colors.muted}10`,
  },
  card: {
    background: colors.surface,
    fontFamily: font.family,
  },
  cardLayout: {
    display: 'flex',
  },
  cardMedia: {
    width: '140px',
    minWidth: '140px',
    maxHeight: '140px',
    objectFit: 'cover' as const,
    display: 'block',
    borderRight: `1px solid ${colors.muted}15`,
  },
  cardBody: {
    flex: 1,
    padding: '12px 16px',
  },
  cardHeader: {
    marginBottom: '6px',
  },
  cardTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  position: {
    fontSize: '16px',
    fontWeight: 700,
    color: colors.cyan,
    fontFamily: font.family,
  },
  adId: {
    fontSize: '12px',
    color: colors.muted,
    fontFamily: font.family,
  },
  copyPreview: {
    fontSize: '13px',
    color: colors.white,
    margin: '0 0 4px',
    lineHeight: 1.4,
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  headline: {
    fontSize: '12px',
    color: colors.muted,
    margin: '0 0 4px',
    fontFamily: font.family,
  },
  annotation: {
    fontSize: '12px',
    color: colors.lightPurple,
    margin: '4px 0 0',
    fontStyle: 'italic',
    fontFamily: font.family,
  },
}
