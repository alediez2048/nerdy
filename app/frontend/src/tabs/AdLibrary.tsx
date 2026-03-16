// PA-09: Ad Library tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchAds } from '../api/dashboard'
import Badge, { StatusBadge } from '../components/Badge'

interface Ad {
  ad_id: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  status: string
  cycle_count: number
  image_path: string | null
  image_url: string | null
}

export default function AdLibrary({ sessionId }: { sessionId: string }) {
  const [ads, setAds] = useState<Ad[]>([])
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAds(sessionId)
      .then((data) => setAds((data.ad_library || []) as Ad[]))
      .catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>

  const filtered = ads.filter((a) => !filter || a.status === filter)
    .sort((a, b) => b.aggregate_score - a.aggregate_score)

  return (
    <div>
      {/* Filters */}
      <div style={s.filterRow}>
        {['', 'published', 'in_progress', 'discarded'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={filter === f ? s.filterActive : s.filterBtn}
          >
            {f || 'All'} {f ? `(${ads.filter((a) => a.status === f).length})` : `(${ads.length})`}
          </button>
        ))}
      </div>

      {/* Ad list */}
      {filtered.length === 0 ? (
        <p style={{ color: colors.muted }}>No ads found</p>
      ) : (
        <div style={s.list}>
          {filtered.map((ad) => (
            <div
              key={ad.ad_id}
              onClick={() => setExpanded(expanded === ad.ad_id ? null : ad.ad_id)}
              style={s.card}
            >
              <div style={s.cardHeader}>
                <span style={s.adId}>{ad.ad_id}</span>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <StatusBadge status={ad.status} />
                  <Badge label={ad.aggregate_score.toFixed(1)} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />
                </div>
              </div>
              <p style={s.copy}>{ad.copy?.primary_text || ad.copy?.headline || '—'}</p>

              {ad.image_url && (
                <img
                  src={`/api${ad.image_url}`}
                  alt={`Ad ${ad.ad_id}`}
                  style={s.adImage}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              )}

              {expanded === ad.ad_id && (
                <div style={s.expanded}>
                  {ad.copy?.headline && <p><strong>Headline:</strong> {ad.copy.headline}</p>}
                  {ad.copy?.description && <p><strong>Description:</strong> {ad.copy.description}</p>}
                  {ad.copy?.cta_button && <p><strong>CTA:</strong> {ad.copy.cta_button}</p>}
                  <div style={s.scoreGrid}>
                    {Object.entries(ad.scores).map(([dim, score]) => (
                      <div key={dim} style={s.scoreItem}>
                        <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace('_', ' ')}</span>
                        <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '—'}</span>
                      </div>
                    ))}
                  </div>
                  <p style={{ fontSize: '12px', color: colors.muted }}>Cycles: {ad.cycle_count}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  filterRow: { display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' },
  filterBtn: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  filterActive: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}20`, color: colors.cyan, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  list: { display: 'flex', flexDirection: 'column', gap: '8px' },
  card: {
    background: colors.surface, borderRadius: radii.input, padding: '14px 18px',
    cursor: 'pointer', fontFamily: font.family,
  },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' },
  adId: { fontSize: '12px', color: colors.muted },
  copy: { fontSize: '14px', color: colors.white, margin: 0, lineHeight: 1.4 },
  adImage: { width: '100%', maxHeight: '220px', objectFit: 'cover' as const, borderRadius: radii.input, marginTop: '10px' },
  expanded: { marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${colors.muted}20`, fontSize: '13px', color: colors.white },
  scoreGrid: { display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginTop: '8px' },
  scoreItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' },
}
