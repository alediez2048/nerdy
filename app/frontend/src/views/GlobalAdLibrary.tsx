// Global Ad Library — standalone view (all sessions, all ads)
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchGlobalDashboard } from '../api/dashboard'
import Badge, { StatusBadge } from '../components/Badge'

interface Ad {
  instance_id: string
  created_at: string
  ad_id: string
  brief_id: string
  session_id?: string | null
  session_label?: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  rationale: Record<string, string>
  status: string
  cycle_count: number
  image_path: string | null
  image_url: string | null
  video_url?: string | null
  video_scores?: Record<string, number> | null
  image_detail_scores?: Record<string, number> | null
  image_avg?: number | null
  video_detail_scores?: Record<string, number> | null
  video_avg?: number | null
  adherence_scores?: Record<string, number> | null
  adherence_avg?: number | null
}

export default function GlobalAdLibrary() {
  const [ads, setAds] = useState<Ad[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState('')
  const [sessionFilter, setSessionFilter] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [archived, setArchived] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('archived_ads')
      return saved ? new Set(JSON.parse(saved)) : new Set()
    } catch { return new Set() }
  })
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    fetchGlobalDashboard('all')
      .then((data) => {
        setAds((data.ad_library || []) as Ad[])
        setLoading(false)
      })
      .catch((e) => { setError(e.message); setLoading(false) })
  }, [])

  const toggleArchive = (instanceId: string) => {
    setArchived((prev) => {
      const next = new Set(prev)
      if (next.has(instanceId)) next.delete(instanceId)
      else next.add(instanceId)
      localStorage.setItem('archived_ads', JSON.stringify([...next]))
      return next
    })
  }

  if (error) return <div style={s.page}><div style={s.inner}><p style={{ color: colors.red }}>{error}</p></div></div>
  if (loading) return <div style={s.page}><div style={s.inner}><p style={{ color: colors.muted }}>Loading ad library...</p></div></div>

  const sessionOptions = Array.from(
    new Map(
      ads.map((ad) => {
        const id = ad.session_id || 'global'
        const label = ad.session_label || ad.session_id || 'Global ledger'
        return [id, { id, label }]
      })
    ).values()
  ).sort((a, b) => a.label.localeCompare(b.label))

  const nonDiscarded = ads.filter((a) => a.status !== 'discarded')

  const filtered = nonDiscarded
    .filter((a) => showArchived ? archived.has(a.instance_id) : !archived.has(a.instance_id))
    .filter((a) => {
      if (!filter) return true
      if (filter === 'video') return !!a.video_url
      if (filter === 'image') return !!a.image_url && !a.video_url
      if (filter === 'copy_only') return !a.image_url && !a.video_url
      return a.status === filter
    })
    .filter((a) => !sessionFilter || (a.session_id || 'global') === sessionFilter)
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))

  return (
    <div style={s.page}>
      <div style={s.inner}>
        <h1 style={s.title}>Ad Library</h1>
        <p style={s.subtitle}>
          All generated ads across every session. Click any card to expand details.
        </p>

        {/* Filters */}
        <div style={s.controls}>
          <div style={s.filterRow}>
            {['', 'published', 'in_progress'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={filter === f ? s.filterActive : s.filterBtn}
              >
                {f || 'All'} ({f ? nonDiscarded.filter((a) => a.status === f).length : nonDiscarded.length})
              </button>
            ))}
            <button
              onClick={() => setFilter(filter === 'copy_only' ? '' : 'copy_only')}
              style={filter === 'copy_only' ? s.filterActive : s.filterBtn}
            >
              Copy Only ({nonDiscarded.filter((a) => !a.video_url && !a.image_url).length})
            </button>
            <button
              onClick={() => setFilter(filter === 'image' ? '' : 'image')}
              style={filter === 'image' ? s.filterActive : s.filterBtn}
            >
              Image ({nonDiscarded.filter((a) => a.image_url && !a.video_url).length})
            </button>
            <button
              onClick={() => setFilter(filter === 'video' ? '' : 'video')}
              style={filter === 'video' ? s.filterActive : s.filterBtn}
            >
              Video ({nonDiscarded.filter((a) => a.video_url).length})
            </button>
            <button
              onClick={() => setShowArchived(!showArchived)}
              style={showArchived ? s.filterActive : s.filterBtn}
            >
              Archived ({archived.size})
            </button>
          </div>
          <label style={s.sessionFilterWrap}>
            <span style={s.sessionFilterLabel}>Session</span>
            <select
              value={sessionFilter}
              onChange={(e) => setSessionFilter(e.target.value)}
              style={s.sessionSelect}
            >
              <option value="">All sessions ({sessionOptions.length})</option>
              {sessionOptions.map((session) => (
                <option key={session.id} value={session.id}>{session.label}</option>
              ))}
            </select>
          </label>
        </div>

        {/* Results */}
        {filtered.length === 0 ? (
          <p style={{ color: colors.muted }}>No ads found</p>
        ) : (
          <div style={s.grid}>
            {filtered.map((ad) => (
              <div
                key={ad.instance_id}
                onClick={() => setExpanded(expanded === ad.instance_id ? null : ad.instance_id)}
                style={s.card}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <StatusBadge status={ad.status} />
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleArchive(ad.instance_id) }}
                    style={s.archiveBtn}
                    title={archived.has(ad.instance_id) ? 'Unarchive' : 'Archive'}
                  >
                    {archived.has(ad.instance_id) ? 'Restore' : 'Archive'}
                  </button>
                </div>

                {/* Score badges */}
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '8px' }}>
                  <Badge label={`Copy ${ad.aggregate_score.toFixed(1)}`} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />
                  {ad.adherence_avg != null && ad.adherence_avg > 0 && (
                    <Badge label={`Brief ${ad.adherence_avg.toFixed(1)}`} color={ad.adherence_avg >= 7 ? colors.mint : colors.yellow} />
                  )}
                  {ad.image_avg != null && ad.image_avg > 0 && (
                    <Badge label={`Img ${ad.image_avg.toFixed(1)}`} color={ad.image_avg >= 7 ? colors.mint : colors.yellow} />
                  )}
                  {ad.video_avg != null && ad.video_avg > 0 && (
                    <Badge label={`Vid ${ad.video_avg.toFixed(1)}`} color={ad.video_avg >= 7 ? colors.mint : colors.yellow} />
                  )}
                </div>

                {/* Ad info */}
                <div style={{ marginBottom: '6px' }}>
                  <span style={{ fontSize: '11px', color: colors.cyan }}>
                    {ad.session_label || ad.session_id || 'global'}
                  </span>
                  {ad.created_at && (
                    <span style={{ fontSize: '11px', color: colors.muted, marginLeft: '8px' }}>
                      {new Date(ad.created_at).toLocaleString()}
                    </span>
                  )}
                </div>

                {/* Copy preview */}
                <p style={{ fontSize: '14px', color: colors.white, margin: 0, lineHeight: 1.4 }}>
                  {ad.copy?.primary_text || ad.copy?.headline || '-'}
                </p>

                {/* Media */}
                {ad.video_url && (
                  <video
                    src={`/api${ad.video_url}`}
                    controls muted playsInline
                    style={s.video}
                    onError={(e) => { (e.target as HTMLVideoElement).style.display = 'none' }}
                  />
                )}
                {ad.image_url && !ad.video_url && (
                  <img
                    src={`/api${ad.image_url}`}
                    alt={ad.ad_id}
                    style={s.image}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                )}

                {/* Expanded details */}
                {expanded === ad.instance_id && (
                  <div style={s.expandedSection}>
                    {ad.copy?.headline && <p><strong>Headline:</strong> {ad.copy.headline}</p>}
                    {ad.copy?.description && <p><strong>Description:</strong> {ad.copy.description}</p>}
                    {ad.copy?.cta_button && <p><strong>CTA:</strong> {ad.copy.cta_button}</p>}

                    {/* Copy scores */}
                    {Object.keys(ad.scores).length > 0 && (
                      <div style={{ marginTop: '10px' }}>
                        <div style={{ fontSize: '11px', color: colors.cyan, fontWeight: 600, marginBottom: '4px' }}>Copy Quality</div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                          {Object.entries(ad.scores).map(([dim, score]) => (
                            <div key={dim} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                              <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace(/_/g, ' ')}</span>
                              <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Brief adherence scores */}
                    {ad.adherence_scores && Object.values(ad.adherence_scores).some((v) => typeof v === 'number' && v > 0) && (
                      <div style={{ marginTop: '10px' }}>
                        <div style={{ fontSize: '11px', color: colors.mint, fontWeight: 600, marginBottom: '4px' }}>Brief Adherence</div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                          {Object.entries(ad.adherence_scores).map(([dim, score]) => (
                            <div key={dim} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                              <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace(/_/g, ' ')}</span>
                              <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Image scores */}
                    {ad.image_detail_scores && Object.values(ad.image_detail_scores).some((v) => typeof v === 'number' && v > 0) && (
                      <div style={{ marginTop: '10px' }}>
                        <div style={{ fontSize: '11px', color: colors.cyan, fontWeight: 600, marginBottom: '4px' }}>Image Quality</div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                          {Object.entries(ad.image_detail_scores).map(([dim, score]) => (
                            <div key={dim} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                              <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace(/_/g, ' ')}</span>
                              <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Video scores */}
                    {ad.video_detail_scores && Object.values(ad.video_detail_scores).some((v) => typeof v === 'number' && v > 0) && (
                      <div style={{ marginTop: '10px' }}>
                        <div style={{ fontSize: '11px', color: colors.cyan, fontWeight: 600, marginBottom: '4px' }}>Video Quality</div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
                          {Object.entries(ad.video_detail_scores).map(([dim, score]) => (
                            <div key={dim} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                              <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace(/_/g, ' ')}</span>
                              <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '-'}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Copy rationales */}
                    {Object.keys(ad.rationale).length > 0 && (
                      <div style={{ marginTop: '10px' }}>
                        {Object.entries(ad.rationale).map(([dim, text]) => text && (
                          <p key={dim} style={{ fontSize: '12px', color: colors.muted, margin: '4px 0' }}>
                            <strong style={{ color: colors.white }}>{dim.replace(/_/g, ' ')}:</strong> {text}
                          </p>
                        ))}
                      </div>
                    )}
                    <p style={{ fontSize: '12px', color: colors.muted }}>Cycles: {ad.cycle_count}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', width: '100%', background: colors.ink, fontFamily: font.family },
  inner: { maxWidth: '1100px', margin: '0 auto', padding: '84px 20px 32px' },
  title: {
    fontSize: '28px', fontWeight: 700, margin: '0 0 4px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  subtitle: { color: colors.muted, fontSize: '13px', margin: '0 0 20px', lineHeight: 1.6 },
  controls: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    gap: '12px', marginBottom: '16px', flexWrap: 'wrap' as const,
  },
  filterRow: { display: 'flex', gap: '8px', flexWrap: 'wrap' as const },
  filterBtn: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  filterActive: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}20`, color: colors.cyan, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  sessionFilterWrap: { display: 'flex', alignItems: 'center', gap: '8px' },
  sessionFilterLabel: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
  sessionSelect: {
    padding: '8px 12px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: colors.surface, color: colors.white, fontSize: '12px', fontFamily: font.family, outline: 'none',
  },
  grid: { columnCount: 3, columnGap: '12px' },
  card: {
    background: colors.surface, borderRadius: radii.input, padding: '14px 18px',
    cursor: 'pointer', fontFamily: font.family, overflow: 'hidden',
    marginBottom: '12px', breakInside: 'avoid' as const,
  },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' },
  video: { width: '100%', maxHeight: '480px', borderRadius: radii.input, marginTop: '10px', background: '#000' },
  image: { width: '100%', maxHeight: '480px', objectFit: 'contain' as const, borderRadius: radii.input, marginTop: '10px' },
  expandedSection: { marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${colors.muted}20`, fontSize: '13px', color: colors.white },
  archiveBtn: {
    padding: '2px 8px', borderRadius: radii.button, border: `1px solid ${colors.muted}30`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontSize: '11px', fontFamily: font.family,
  },
}
