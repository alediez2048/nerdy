// PA-09: Competitive Intel tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCompetitive } from '../api/dashboard'

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

export default function CompetitiveIntel() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCompetitive().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading competitive intelligence...</p>
  if (Object.keys(data).length === 0) return <p style={{ color: colors.muted }}>No competitive data available</p>

  const hookDist = (data.hook_distribution || data.hook_type_counts || data.hook_types || {}) as Record<string, number>
  const strategyRadar = (data.strategy_radar || {}) as Record<string, Record<string, number>>
  const gapAnalysis = (data.gap_analysis || []) as GapItem[]
  const summaries = (data.competitor_summaries || {}) as Record<string, CompSummary>
  const metadata = (data.metadata || {}) as Metadata

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
            Each competitor's approach distilled from their active ad library. Use gaps to identify
            positioning opportunities — areas where competitors aren't competing.
          </p>
          <div style={s.compGrid}>
            {Object.entries(summaries).map(([name, info]) => (
              <div key={name} style={s.compCard}>
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
            ))}
          </div>
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
}
