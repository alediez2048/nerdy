// PA-09: Ad Library tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchAds } from '../api/dashboard'
import { addAdToCurated } from '../api/curation'
import Badge, { StatusBadge } from '../components/Badge'

interface Ad {
  ad_id: string
  instance_id: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  status: string
  cycle_count: number
  image_path: string | null
  image_url: string | null
  video_url?: string | null
  video_remote_url?: string | null
  video_scores?: Record<string, number> | null
  image_detail_scores?: Record<string, number> | null
  image_avg?: number | null
  video_detail_scores?: Record<string, number> | null
  video_avg?: number | null
  adherence_scores?: Record<string, number> | null
  adherence_avg?: number | null
}

function logVideoRenderDebug(adId: string, src: string, el: HTMLVideoElement) {
  // region agent log
  fetch('http://127.0.0.1:7469/ingest/08f59445-601e-4fe3-9043-420e593807a7',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'c163a9'},body:JSON.stringify({sessionId:'c163a9',runId:'pre-fix',hypothesisId:'H11',location:'app/frontend/src/tabs/AdLibrary.tsx:logVideoRenderDebug',message:'video element render characteristics',data:{adId,src,filter:window.getComputedStyle(el).filter,mixBlendMode:window.getComputedStyle(el).mixBlendMode,opacity:window.getComputedStyle(el).opacity,backgroundColor:window.getComputedStyle(el).backgroundColor,videoWidth:el.videoWidth,videoHeight:el.videoHeight},timestamp:Date.now()})}).catch(()=>{});
  // endregion
}

export default function AdLibrary({ sessionId, sessionType = 'image' }: { sessionId: string; sessionType?: string }) {
  const [ads, setAds] = useState<Ad[]>([])
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [curatedIds, setCuratedIds] = useState<Set<string>>(new Set())

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

      {/* Ad grid */}
      {filtered.length === 0 ? (
        <p style={{ color: colors.muted }}>No ads found</p>
      ) : (
        <div style={s.grid}>
          {filtered.map((ad) => {
            const uid = ad.instance_id || ad.ad_id
            const isExpanded = expanded.has(uid)
            const toggle = () => setExpanded((prev) => {
              const next = new Set(prev)
              next.has(uid) ? next.delete(uid) : next.add(uid)
              return next
            })
            const isVideo = sessionType === 'video'
            const effectiveVideoUrl = ad.video_url || ad.video_remote_url
            const hasVideo = isVideo && effectiveVideoUrl
            const videoSrc = effectiveVideoUrl
              ? effectiveVideoUrl.startsWith('http') ? effectiveVideoUrl : `/api${effectiveVideoUrl}`
              : ''

            if (isExpanded) {
              return (
                <div
                  key={uid}
                  onClick={toggle}
                  style={{ ...s.card, ...s.cardExpanded }}
                >
                  <div style={s.expandedLayout}>
                    {hasVideo ? (
                      <video
                        src={videoSrc}
                        controls
                        style={s.adVideoExpanded}
                        onLoadedData={(e) => logVideoRenderDebug(ad.ad_id, videoSrc, e.currentTarget)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    ) : ad.image_url ? (
                      <img
                        src={`/api${ad.image_url}`}
                        alt={`Ad ${ad.ad_id}`}
                        style={s.adImageExpanded}
                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                      />
                    ) : isVideo ? (
                      <div style={s.noVideoPlaceholder}>
                        <span style={{ fontSize: '32px' }}>🎬</span>
                        <span style={{ color: colors.muted, fontSize: '12px' }}>Copy only</span>
                      </div>
                    ) : null}
                    <div style={s.expandedDetails}>
                      <div style={s.cardHeader}>
                        <span style={s.adId}>{ad.ad_id}</span>
                        <div style={{ display: 'flex', gap: '4px', alignItems: 'center', flexWrap: 'wrap' }}>
                          <StatusBadge status={ad.status} />
                          <Badge label={`Copy: ${ad.aggregate_score.toFixed(1)}`} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />
                          {ad.adherence_avg != null && ad.adherence_avg > 0 && (
                            <Badge label={`Brief: ${ad.adherence_avg.toFixed(1)}`} color={ad.adherence_avg >= 7 ? colors.mint : colors.yellow} />
                          )}
                          {ad.image_avg != null && ad.image_avg > 0 && (
                            <Badge label={`Img: ${ad.image_avg.toFixed(1)}`} color={ad.image_avg >= 7 ? colors.mint : colors.yellow} />
                          )}
                          {ad.video_avg != null && ad.video_avg > 0 && (
                            <Badge label={`Vid: ${ad.video_avg.toFixed(1)}`} color={ad.video_avg >= 7 ? colors.mint : colors.yellow} />
                          )}
                        </div>
                      </div>
                      <p style={s.copyFull}>
                        {ad.copy?.primary_text || ad.copy?.headline || '—'}
                      </p>
                      <div style={s.detailSection}>
                        {ad.copy?.headline && <p style={{ margin: '4px 0' }}><strong>Headline:</strong> {ad.copy.headline}</p>}
                        {ad.copy?.description && <p style={{ margin: '4px 0' }}><strong>Description:</strong> {ad.copy.description}</p>}
                        {ad.copy?.cta_button && <p style={{ margin: '4px 0' }}><strong>CTA:</strong> {ad.copy.cta_button}</p>}
                      </div>
                      <p style={{ color: colors.muted, fontSize: '11px', margin: '8px 0 4px' }}>Copy Scores (text evaluation only)</p>
                      <div style={s.scoreGrid}>
                        {Object.entries(ad.scores).map(([dim, score]) => (
                          <div key={dim} style={s.scoreItem}>
                            <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace('_', ' ')}</span>
                            <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '—'}</span>
                          </div>
                        ))}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px', padding: '0 14px' }}>
                        {!isVideo && <p style={{ fontSize: '12px', color: colors.muted, margin: 0 }}>Cycles: {ad.cycle_count}</p>}
                        {hasVideo && (
                          <a
                            href={videoSrc}
                            download
                            onClick={(e) => e.stopPropagation()}
                            style={s.downloadBtn}
                          >
                            Download MP4
                          </a>
                        )}
                        {ad.status === 'published' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              addAdToCurated(sessionId, ad.ad_id, 0)
                                .then(() => setCuratedIds((prev) => new Set(prev).add(ad.ad_id)))
                                .catch(() => {})
                            }}
                            style={curatedIds.has(ad.ad_id) ? s.curatedBtnDone : s.curateBtn}
                            disabled={curatedIds.has(ad.ad_id)}
                          >
                            {curatedIds.has(ad.ad_id) ? 'Added to Curated Set' : 'Add to Curated Set'}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )
            }
            return (
              <div
                key={uid}
                onClick={toggle}
                style={s.card}
              >
                {hasVideo ? (
                  <video
                    src={videoSrc}
                    muted
                    style={s.adVideo}
                    onLoadedData={(e) => logVideoRenderDebug(ad.ad_id, videoSrc, e.currentTarget)}
                    onMouseEnter={(e) => (e.target as HTMLVideoElement).play().catch(() => {})}
                    onMouseLeave={(e) => { const v = e.target as HTMLVideoElement; v.pause(); v.currentTime = 0 }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : ad.image_url ? (
                  <img
                    src={`/api${ad.image_url}`}
                    alt={`Ad ${ad.ad_id}`}
                    style={s.adImage}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                ) : isVideo ? (
                  <div style={s.noVideoThumb}>
                    <span style={{ fontSize: '24px' }}>🎬</span>
                    <span style={{ color: colors.muted, fontSize: '11px' }}>Copy only</span>
                  </div>
                ) : null}
                <div style={s.cardHeader}>
                  <span style={s.adId}>{ad.ad_id}</span>
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <StatusBadge status={ad.status} />
                    <Badge label={`Copy: ${ad.aggregate_score.toFixed(1)}`} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />
                    {ad.image_avg != null && ad.image_avg > 0 && (
                      <Badge label={`Img: ${ad.image_avg.toFixed(1)}`} color={ad.image_avg >= 7 ? colors.mint : colors.yellow} />
                    )}
                    {ad.video_avg != null && ad.video_avg > 0 && (
                      <Badge label={`Vid: ${ad.video_avg.toFixed(1)}`} color={ad.video_avg >= 7 ? colors.mint : colors.yellow} />
                    )}
                  </div>
                </div>
                <p style={s.copy}>
                  {ad.copy?.primary_text || ad.copy?.headline || '—'}
                </p>
              </div>
            )
          })}
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
  grid: {
    display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px',
  },
  card: {
    background: colors.surface, borderRadius: radii.card, padding: '0',
    cursor: 'pointer', fontFamily: font.family, overflow: 'hidden',
    transition: 'box-shadow 0.2s ease',
  },
  cardExpanded: {
    gridColumn: '1 / -1',
  },
  cardHeader: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '10px 14px 4px',
  },
  adId: { fontSize: '11px', color: colors.muted, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '55%' },
  copy: {
    fontSize: '13px', color: colors.white, margin: 0, lineHeight: 1.4,
    padding: '0 14px 12px',
    display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' as const,
    overflow: 'hidden',
  },
  copyFull: {
    fontSize: '13px', color: colors.white, margin: 0, lineHeight: 1.4,
    padding: '0 14px 12px',
  },
  adImage: {
    width: '100%', objectFit: 'cover' as const, display: 'block',
  },
  expandedLayout: {
    display: 'flex', gap: '0',
  },
  adImageExpanded: {
    width: '280px', minWidth: '280px', maxHeight: '400px',
    objectFit: 'cover' as const, display: 'block',
    background: colors.surface,
    borderRight: `1px solid ${colors.muted}20`,
  },
  expandedDetails: {
    flex: 1, padding: '4px 0 14px', fontSize: '13px', color: colors.white,
    display: 'flex', flexDirection: 'column' as const,
  },
  detailSection: {
    padding: '0 14px', borderTop: `1px solid ${colors.muted}20`,
    paddingTop: '10px', marginTop: '4px',
  },
  scoreGrid: { display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginTop: '8px' },
  scoreItem: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' },
  curateBtn: {
    padding: '5px 14px', borderRadius: radii.button, border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink, fontWeight: 600, fontSize: '12px', cursor: 'pointer', fontFamily: font.family,
  },
  curatedBtnDone: {
    padding: '5px 14px', borderRadius: radii.button, border: `1px solid ${colors.mint}40`,
    background: 'transparent', color: colors.mint, fontSize: '12px', cursor: 'default', fontFamily: font.family,
  },
  adVideo: {
    width: '100%', aspectRatio: '9/16', objectFit: 'cover' as const, display: 'block',
    background: '#000', cursor: 'pointer',
  },
  adVideoExpanded: {
    width: '280px', minWidth: '280px', maxHeight: '500px',
    objectFit: 'contain' as const, display: 'block',
    background: '#000',
    borderRight: `1px solid ${colors.muted}20`,
  },
  noVideoThumb: {
    width: '100%', aspectRatio: '9/16',
    display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center',
    gap: '4px', background: `${colors.muted}10`,
  },
  noVideoPlaceholder: {
    width: '280px', minWidth: '280px', minHeight: '200px',
    display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center',
    gap: '8px', background: `${colors.muted}10`,
    borderRight: `1px solid ${colors.muted}20`,
  },
  downloadBtn: {
    padding: '5px 14px', borderRadius: radii.button, border: `1px solid ${colors.cyan}40`,
    background: 'transparent', color: colors.cyan, fontSize: '12px', cursor: 'pointer',
    fontFamily: font.family, textDecoration: 'none',
  },
}
