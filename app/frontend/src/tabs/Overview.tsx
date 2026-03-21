// PA-09: Overview tab — hero metrics + quality trend
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchSummary } from '../api/dashboard'

export default function Overview({ sessionId, sessionType = 'image' }: { sessionId: string; sessionType?: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  useEffect(() => {
    fetchSummary(sessionId).then(setData).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading...</p>

  const summary = (data.pipeline_summary || {}) as Record<string, unknown>
  const results = (data.results_summary || {}) as Record<string, unknown>

  const isVideo = sessionType === 'video'

  const costUsd =
    typeof summary.total_cost_usd === 'number'
      ? summary.total_cost_usd
      : typeof results.cost_so_far === 'number'
        ? results.cost_so_far
        : undefined

  const variantJobs =
    typeof results.video_variants_generated === 'number'
      ? results.video_variants_generated
      : undefined

  /** Matches Ad Library: rows with a final video file (same count as playable clips in the library). */
  const videosInLibrary =
    typeof summary.videos_in_library === 'number' ? summary.videos_in_library : undefined

  const metrics = isVideo
    ? [
        {
          label: 'Video ads',
          value:
            videosInLibrary ??
            results.videos_generated ??
            summary.total_ads_generated ??
            '—',
          tip:
            'Number of videos listed in the Ad Library for this session (final output files). This matches what you see there.',
        },
        {
          label: 'Fal jobs',
          value: variantJobs ?? '—',
          tip:
            'Billable video generations (one per variant). Two jobs per ad is normal for A/B variants.',
        },
        { label: 'Selected', value: results.videos_selected ?? '—',
          tip: 'Winning clips after evaluation (one pick per ad when variants exist).' },
        { label: 'Blocked', value: results.videos_blocked ?? '—',
          tip: 'Ads where no clip passed thresholds.' },
        { label: 'Total Cost', value: costUsd !== undefined ? `$${costUsd.toFixed(2)}` : '—',
          tip:
            'Estimated spend: Gemini + image/video rates. For video, Fal cost counts the winning variant per ad (not the A/B alternate). Tune rates in data/config.yaml to match Usage.',
        },
      ]
    : [
        { label: 'Ads Generated', value: summary.total_ads_generated ?? results.ads_generated ?? '—',
          tip: 'Total number of ad variants created across all cycles, including regeneration attempts.' },
        { label: 'Published', value: summary.total_ads_published ?? results.ads_published ?? '—',
          tip: 'Ads that met the quality threshold (7.0+) and passed compliance checks.' },
        { label: 'Publish Rate', value: summary.publish_rate ? `${((summary.publish_rate as number) * 100).toFixed(0)}%` : '—',
          tip: 'Percentage of generated ads that scored above threshold. Higher = better brief quality and fewer wasted tokens.' },
        { label: 'Avg Copy Score', value: summary.avg_score ?? results.avg_score ?? '—',
          tip: 'Mean weighted copy score across 5 dimensions (Clarity, Value Prop, CTA, Brand Voice, Emotional Resonance) for published ads. Image and video quality are not scored.' },
        { label: 'Total Cost', value: costUsd !== undefined ? `$${costUsd.toFixed(2)}` : '—',
          tip: 'Estimated API spend for generation, evaluation, and image creation. Based on token counts and per-model pricing.' },
        { label: 'Total Tokens', value: summary.total_tokens ? (summary.total_tokens as number).toLocaleString() : '—',
          tip: 'Sum of input + output tokens consumed across all LLM and image API calls in this session.' },
      ]

  return (
    <div>
      <div style={s.grid}>
        {metrics.map((m, i) => (
          <div
            key={m.label}
            style={{ ...s.metricCard, ...(hoveredIdx === i ? s.metricCardHover : {}) }}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <div style={s.metricValue}>{String(m.value)}</div>
            <div style={s.metricLabel}>{m.label}</div>
            {hoveredIdx === i && (
              <div style={s.tooltip}>{m.tip}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '12px' },
  metricCard: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px',
    textAlign: 'center',
    position: 'relative',
    cursor: 'default',
    transition: 'border-color 0.15s ease',
    border: `1px solid transparent`,
  },
  metricCardHover: {
    borderColor: `${colors.cyan}60`,
  },
  metricValue: { fontSize: '24px', fontWeight: 700, color: colors.white, fontFamily: font.family },
  metricLabel: { fontSize: '12px', color: colors.muted, marginTop: '4px', fontFamily: font.family },
  tooltip: {
    position: 'absolute',
    left: '50%',
    bottom: 'calc(100% + 8px)',
    transform: 'translateX(-50%)',
    background: colors.ink,
    border: `1px solid ${colors.muted}40`,
    borderRadius: radii.input,
    padding: '10px 14px',
    fontSize: '12px',
    lineHeight: '1.5',
    color: colors.white,
    fontFamily: font.family,
    width: '240px',
    textAlign: 'left',
    zIndex: 10,
    boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
  },
}
