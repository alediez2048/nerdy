// PA-09 + PD-10: Competitive Intel tab with Raw Ads Browser
import { useEffect, useState, useCallback } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCompetitive, fetchCompetitiveAds } from '../api/dashboard'

interface CompSummary {
  strategy: string
  dominant_hooks: string[]
  emotional_levers: string[]
  gaps: string
}

interface GapItem {
  hook_type: string
  coverage_pct: number
  opportunity: string
}

interface Metadata {
  total_ads_scraped?: number
  unique_ads?: number
  pattern_records?: number
  source?: string
  competitors?: string[]
}

interface RawAd {
  'Ad Library ID': string
  'Ad Text Content': string
  'Ad Creative Image': string
  'Advertiser Name': string
  'Started Running Date': string
  Platforms: string
  _competitor: string
  _hook_type?: string
  _emotional_register?: string
  _body_pattern?: string
  _cta_style?: string
}

interface RawAdsResponse {
  ads: RawAd[]
  total: number
  offset: number
  limit: number
  competitors: string[]
}

export default function CompetitiveIntel() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedCompetitor, setSelectedCompetitor] = useState<string | null>(null)
  const [rawAds, setRawAds] = useState<RawAd[]>([])
  const [rawAdsTotal, setRawAdsTotal] = useState(0)
  const [rawAdsLoading, setRawAdsLoading] = useState(false)
  const [rawAdsError, setRawAdsError] = useState<string | null>(null)
  const [hookFilter, setHookFilter] = useState<string | null>(null)
  const [rawAdsOffset, setRawAdsOffset] = useState(0)
  const RAW_ADS_LIMIT = 50

  useEffect(() => {
    fetchCompetitive().then(setData).catch((e) => setError(e.message))
  }, [])

  const loadRawAds = useCallback(
    (competitor: string, hook?: string | null, offset = 0) => {
      setRawAdsLoading(true)
      setRawAdsError(null)
      const params: { competitor: string; hook_type?: string; offset: number; limit: number } = {
        competitor,
        offset,
        limit: RAW_ADS_LIMIT,
      }
      if (hook) params.hook_type = hook
      fetchCompetitiveAds(params)
        .then((resp) => {
          const typed = resp as unknown as RawAdsResponse
          setRawAds(typed.ads || [])
          setRawAdsTotal(typed.total || 0)
          setRawAdsOffset(offset)
        })
        .catch((e) => setRawAdsError(e.message))
        .finally(() => setRawAdsLoading(false))
    },
    [],
  )

  const handleCompetitorClick = (name: string) => {
    // Convert display name to filename key (e.g. "Chegg" -> "chegg", "Varsity Tutors" -> "varsity_tutors")
    const key = name.toLowerCase().replace(/\s+/g, '_')
    if (selectedCompetitor === key) {
      setSelectedCompetitor(null)
      setRawAds([])
      setHookFilter(null)
      return
    }
    setSelectedCompetitor(key)
    setHookFilter(null)
    loadRawAds(key)
  }

  const handleHookFilter = (hook: string) => {
    if (!selectedCompetitor) return
    const next = hookFilter === hook ? null : hook
    setHookFilter(next)
    loadRawAds(selectedCompetitor, next)
  }

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading competitive intelligence...</p>
  if (Object.keys(data).length === 0) return <p style={{ color: colors.muted }}>No competitive data available</p>

  const hookDist = (data.hook_distribution || data.hook_type_counts || data.hook_types || {}) as Record<string, number>
  const strategyRadar = (data.strategy_radar || {}) as Record<string, Record<string, number>>
  const gapAnalysis = (data.gap_analysis || []) as GapItem[]
  const summaries = (data.competitor_summaries || {}) as Record<string, CompSummary>
  const metadata = (data.metadata || {}) as Metadata

  // Collect unique hook types from loaded raw ads for filter chips
  const hookTypes = Array.from(new Set(rawAds.map((a) => a._hook_type).filter(Boolean))) as string[]

  return (
    <div>
      {/* Header */}
      <div style={s.header}>
        <p style={s.desc}>
          Competitive patterns extracted from {metadata.total_ads_scraped || '200+' } ads
          across {metadata.competitors?.length || 4} competitors via Meta Ad Library.
          These patterns inform the pipeline's reference-decompose-recombine strategy — the system learns
          what hooks, CTAs, and emotional angles competitors use, then generates differentiated ads.
        </p>
      </div>

      {/* Competitor Strategy Cards */}
      {Object.keys(summaries).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Competitor Strategies</h3>
          <p style={s.desc}>
            Each competitor's approach distilled from their active ad library. Click a card to browse
            their raw ads from Meta Ad Library.
          </p>
          <div style={s.compGrid}>
            {Object.entries(summaries).map(([name, info]) => {
              const key = name.toLowerCase().replace(/\s+/g, '_')
              const isSelected = selectedCompetitor === key
              return (
                <div
                  key={name}
                  style={{
                    ...s.compCard,
                    cursor: 'pointer',
                    border: isSelected ? `2px solid ${colors.cyan}` : '2px solid transparent',
                    transition: 'border-color 0.2s',
                  }}
                  onClick={() => handleCompetitorClick(name)}
                >
                  <div style={s.compName}>{name}</div>
                  <p style={s.compStrategy}>{info.strategy}</p>
                  <div style={s.tagRow}>
                    {info.dominant_hooks?.map((h) => (
                      <span key={h} style={s.hookTag}>{h.replace(/_/g, ' ')}</span>
                    ))}
                    {info.emotional_levers?.map((e) => (
                      <span key={e} style={s.emotionTag}>{e.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                  {info.gaps && (
                    <div style={s.gapNote}>
                      <strong>Gaps:</strong> {info.gaps}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Raw Ads Browser (PD-10) */}
      {selectedCompetitor && (
        <div style={s.section}>
          <h3 style={s.heading}>
            Raw Ads — {selectedCompetitor.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
          </h3>
          <p style={s.desc}>
            Actual ads scraped from Meta Ad Library. {rawAdsTotal} ads found.
            {hookTypes.length > 0 && ' Filter by hook type below.'}
          </p>

          {/* Hook type filter chips */}
          {hookTypes.length > 0 && (
            <div style={{ ...s.tagRow, marginBottom: '16px' }}>
              {hookTypes.map((ht) => (
                <span
                  key={ht}
                  onClick={() => handleHookFilter(ht)}
                  style={{
                    ...s.hookTag,
                    cursor: 'pointer',
                    background: hookFilter === ht ? colors.cyan : `${colors.cyan}20`,
                    color: hookFilter === ht ? colors.ink : colors.cyan,
                    fontWeight: hookFilter === ht ? 700 : 400,
                    transition: 'all 0.15s',
                  }}
                >
                  {ht.replace(/_/g, ' ')}
                </span>
              ))}
              {hookFilter && (
                <span
                  onClick={() => handleHookFilter(hookFilter)}
                  style={{ ...s.hookTag, cursor: 'pointer', color: colors.muted, background: `${colors.muted}20` }}
                >
                  clear filter
                </span>
              )}
            </div>
          )}

          {rawAdsLoading && <p style={{ color: colors.muted, fontSize: '13px' }}>Loading ads...</p>}
          {rawAdsError && <p style={{ color: colors.red, fontSize: '13px' }}>{rawAdsError}</p>}

          {!rawAdsLoading && rawAds.length === 0 && !rawAdsError && (
            <p style={{ color: colors.muted, fontSize: '13px' }}>No ads found for this filter.</p>
          )}

          {!rawAdsLoading && rawAds.length > 0 && (
            <>
              <div style={s.adGrid}>
                {rawAds.map((ad) => (
                  <RawAdCard key={ad['Ad Library ID']} ad={ad} />
                ))}
              </div>

              {/* Pagination */}
              {rawAdsTotal > RAW_ADS_LIMIT && (
                <div style={{ display: 'flex', gap: '12px', marginTop: '16px', alignItems: 'center' }}>
                  <button
                    disabled={rawAdsOffset === 0}
                    onClick={() => loadRawAds(selectedCompetitor, hookFilter, Math.max(0, rawAdsOffset - RAW_ADS_LIMIT))}
                    style={s.pageBtn}
                  >
                    Previous
                  </button>
                  <span style={{ fontSize: '12px', color: colors.muted, fontFamily: font.family }}>
                    {rawAdsOffset + 1}–{Math.min(rawAdsOffset + RAW_ADS_LIMIT, rawAdsTotal)} of {rawAdsTotal}
                  </span>
                  <button
                    disabled={rawAdsOffset + RAW_ADS_LIMIT >= rawAdsTotal}
                    onClick={() => loadRawAds(selectedCompetitor, hookFilter, rawAdsOffset + RAW_ADS_LIMIT)}
                    style={s.pageBtn}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Hook Distribution */}
      <div style={s.section}>
        <h3 style={s.heading}>Hook Type Distribution</h3>
        <p style={s.desc}>
          How often each hook type appears across all competitor ads. The pipeline avoids
          over-indexed hooks (high bars) and explores under-used ones for differentiation.
        </p>
        <DistChart data={hookDist} color={colors.cyan} />
      </div>

      {/* Per-Competitor Breakdown */}
      {Object.keys(strategyRadar).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Hook Usage by Competitor</h3>
          <p style={s.desc}>
            Which hooks each competitor relies on most. Reveals strategic clustering —
            if all competitors lean on "direct_offer", that's a crowded lane.
          </p>
          {Object.entries(strategyRadar).map(([comp, hooks]) => (
            <div key={comp} style={{ marginBottom: '20px' }}>
              <div style={s.subheading}>{comp}</div>
              <DistChart data={hooks} color={colors.lightPurple} />
            </div>
          ))}
        </div>
      )}

      {/* Gap Analysis */}
      {gapAnalysis.length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Opportunity Gaps</h3>
          <p style={s.desc}>
            Hook types with less than 15% competitor usage — areas where a strong ad
            could stand out with minimal competitive noise.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '8px' }}>
            {gapAnalysis.map((g) => (
              <div key={g.hook_type} style={s.gapRow}>
                <span style={s.gapHook}>{g.hook_type.replace(/_/g, ' ')}</span>
                <span style={s.gapPct}>{g.coverage_pct.toFixed(0)}%</span>
                <span style={s.gapOpp}>{g.opportunity}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Source note */}
      {metadata.source && (
        <p style={{ fontSize: '11px', color: colors.muted, fontFamily: font.family, marginTop: '24px' }}>
          Source: {metadata.source} · {metadata.pattern_records || 0} patterns
          from {metadata.unique_ads || 0} unique ads
        </p>
      )}
    </div>
  )
}

/** Single raw ad card (PD-10) */
function RawAdCard({ ad }: { ad: RawAd }) {
  const text = ad['Ad Text Content'] || ''
  const truncated = text.length > 180 ? text.slice(0, 180) + '...' : text
  const imageUrl = ad['Ad Creative Image'] || ''
  const platforms = (ad.Platforms || '').split('\n').filter(Boolean)
  const date = ad['Started Running Date'] || ''

  return (
    <div style={s.adCard}>
      {imageUrl && (
        <img
          src={imageUrl}
          alt="Ad creative"
          style={s.adImage}
          loading="lazy"
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
        />
      )}
      <div style={s.adBody}>
        <p style={s.adText}>{truncated || '(no text)'}</p>
        <div style={s.tagRow}>
          {ad._hook_type && (
            <span style={s.hookTag}>{ad._hook_type.replace(/_/g, ' ')}</span>
          )}
          {ad._emotional_register && (
            <span style={s.emotionTag}>{ad._emotional_register.replace(/_/g, ' ')}</span>
          )}
        </div>
        <div style={s.adMeta}>
          {platforms.length > 0 && (
            <span style={s.adMetaItem}>{platforms.join(', ')}</span>
          )}
          {date && <span style={s.adMetaItem}>{date}</span>}
        </div>
      </div>
    </div>
  )
}

function DistChart({ data, color }: { data: Record<string, number>; color: string }) {
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a).slice(0, 10)
  const max = sorted[0]?.[1] || 1

  if (sorted.length === 0) return <p style={{ color: colors.muted, fontSize: '13px' }}>No data</p>

  return (
    <div>
      {sorted.map(([label, count]) => (
        <div key={label} style={s.barRow}>
          <span style={s.barLabel}>{label.replace(/_/g, ' ')}</span>
          <div style={s.barTrack}>
            <div style={{ width: `${(count / max) * 100}%`, height: '100%', background: color, borderRadius: '4px' }} />
          </div>
          <span style={s.barValue}>
            {typeof count === 'number' && count < 1 ? `${(count * 100).toFixed(0)}%` : count}
          </span>
        </div>
      ))}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  header: { marginBottom: '24px' },
  section: { marginBottom: '32px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 4px', fontFamily: font.family },
  subheading: { fontSize: '13px', fontWeight: 600, color: colors.cyan, marginBottom: '8px', fontFamily: font.family },
  desc: { fontSize: '13px', color: colors.muted, margin: '0 0 14px', lineHeight: 1.5, fontFamily: font.family, maxWidth: '720px' },
  compGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' },
  compCard: {
    background: colors.surface, borderRadius: radii.card, padding: '18px',
    fontFamily: font.family,
  },
  compName: { fontSize: '15px', fontWeight: 700, color: colors.white, marginBottom: '8px' },
  compStrategy: { fontSize: '13px', color: colors.muted, lineHeight: 1.5, margin: '0 0 10px' },
  tagRow: { display: 'flex', gap: '6px', flexWrap: 'wrap' as const, marginBottom: '10px' },
  hookTag: {
    fontSize: '11px', padding: '3px 8px', borderRadius: '100px',
    background: `${colors.cyan}20`, color: colors.cyan, fontFamily: font.family,
  },
  emotionTag: {
    fontSize: '11px', padding: '3px 8px', borderRadius: '100px',
    background: `${colors.lightPurple}20`, color: colors.lightPurple, fontFamily: font.family,
  },
  gapNote: {
    fontSize: '12px', color: colors.yellow, lineHeight: 1.4,
    borderTop: `1px solid ${colors.muted}20`, paddingTop: '8px', marginTop: '4px',
  },
  barRow: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' },
  barLabel: { width: '140px', fontSize: '12px', color: colors.muted, textAlign: 'right' as const, fontFamily: font.family },
  barTrack: { flex: 1, height: '16px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' },
  barValue: { fontSize: '12px', color: colors.white, width: '36px', fontFamily: font.family },
  gapRow: {
    display: 'flex', gap: '12px', alignItems: 'center',
    background: colors.surface, borderRadius: radii.input, padding: '10px 14px',
    fontFamily: font.family,
  },
  gapHook: { fontSize: '13px', color: colors.white, fontWeight: 600, minWidth: '120px' },
  gapPct: { fontSize: '13px', color: colors.yellow, fontWeight: 600, minWidth: '40px' },
  gapOpp: { fontSize: '12px', color: colors.muted, flex: 1 },
  // PD-10: Raw Ads Browser styles
  adGrid: {
    display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '14px',
  },
  adCard: {
    background: colors.surface, borderRadius: radii.card, overflow: 'hidden',
    fontFamily: font.family, display: 'flex', flexDirection: 'column' as const,
  },
  adImage: {
    width: '100%', height: '160px', objectFit: 'cover' as const,
    borderTopLeftRadius: radii.card, borderTopRightRadius: radii.card,
    background: `${colors.muted}20`,
  },
  adBody: { padding: '14px', display: 'flex', flexDirection: 'column' as const, gap: '8px', flex: 1 },
  adText: { fontSize: '12px', color: colors.white, lineHeight: 1.5, margin: 0 },
  adMeta: {
    display: 'flex', gap: '10px', flexWrap: 'wrap' as const, marginTop: 'auto',
  },
  adMetaItem: { fontSize: '11px', color: colors.muted, fontFamily: font.family },
  pageBtn: {
    padding: '6px 16px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.white, fontSize: '12px', fontFamily: font.family,
    cursor: 'pointer',
  },
}
