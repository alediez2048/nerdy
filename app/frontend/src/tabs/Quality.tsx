// PA-09: Quality trends tab
import { useEffect, useState } from 'react'
import { colors, font } from '../design/tokens'
import { fetchCycles } from '../api/dashboard'
import Sparkline from '../components/Sparkline'

export default function Quality({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCycles(sessionId).then(setData).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading...</p>

  const trends = (data.quality_trends || {}) as Record<string, unknown>
  const batchScores = (trends.batch_scores || []) as { batch: number; avg_score: number; published: number; generated: number; publish_rate: number }[]
  const distribution = (trends.score_distribution || []) as number[]

  const totalAds = distribution.reduce((a, b) => a + b, 0)
  const publishable = distribution.slice(7).reduce((a, b) => a + b, 0)

  return (
    <div>
      {/* Batch score trend */}
      <div style={s.section}>
        <h3 style={s.heading}>Quality Over Batches</h3>
        <p style={s.desc}>
          Each batch processes up to 10 ads in parallel. The average score tracks whether the
          pipeline is improving across batches via the quality ratchet — the publish threshold
          only goes up, never down.
        </p>
        {batchScores.length > 0 ? (
          <div style={s.chartRow}>
            <Sparkline data={batchScores.map((b) => b.avg_score)} width={300} height={60} />
            <div style={s.batchList}>
              {batchScores.map((b) => (
                <div key={b.batch} style={s.batchItem}>
                  <span style={{ color: colors.muted }}>Batch {b.batch}</span>
                  <span style={{ color: colors.white, fontWeight: 600 }}>{b.avg_score.toFixed(1)}</span>
                  <span style={{ color: colors.mint, fontSize: '12px' }}>{b.published}/{b.generated} published</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ color: colors.muted }}>No batch data yet</p>
        )}
      </div>

      {/* Score distribution */}
      <div style={s.section}>
        <h3 style={s.heading}>Score Distribution</h3>
        <p style={s.desc}>
          How ad scores are spread across the 0–10 scale. Each bar shows how many ads
          scored within that range. Scores are the weighted average of 5 dimensions:
          Clarity, Value Proposition, CTA, Brand Voice, and Emotional Resonance.
        </p>
        <div style={s.distRow}>
          {distribution.map((count, i) => (
            <div key={i} style={s.distBar}>
              {count > 0 && (
                <div style={s.barCount}>{count}</div>
              )}
              <div
                style={{
                  height: `${Math.min(count * 8, 100)}px`,
                  width: '100%',
                  background: i >= 7 ? colors.mint : i >= 5 ? colors.yellow : colors.red,
                  borderRadius: '4px 4px 0 0',
                }}
              />
              <div style={{ fontSize: '10px', color: colors.muted, marginTop: '2px' }}>{i}–{i + 1}</div>
            </div>
          ))}
        </div>
        <div style={s.legend}>
          <span style={s.legendItem}><span style={{ ...s.legendDot, background: colors.mint }} /> 7+ Publishable</span>
          <span style={s.legendItem}><span style={{ ...s.legendDot, background: colors.yellow }} /> 5–7 Improvable</span>
          <span style={s.legendItem}><span style={{ ...s.legendDot, background: colors.red }} /> &lt;5 Below standard</span>
          {totalAds > 0 && (
            <span style={{ ...s.legendItem, marginLeft: 'auto', color: colors.white }}>
              {publishable}/{totalAds} ads publishable ({totalAds > 0 ? ((publishable / totalAds) * 100).toFixed(0) : 0}%)
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: '32px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 4px', fontFamily: font.family },
  desc: { fontSize: '13px', color: colors.muted, margin: '0 0 14px', lineHeight: 1.5, fontFamily: font.family, maxWidth: '680px' },
  chartRow: { display: 'flex', gap: '24px', alignItems: 'flex-start' },
  batchList: { display: 'flex', flexDirection: 'column', gap: '6px' },
  batchItem: { display: 'flex', gap: '12px', fontSize: '13px', fontFamily: font.family },
  distRow: { display: 'flex', gap: '4px', alignItems: 'flex-end', height: '120px' },
  distBar: { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', textAlign: 'center' },
  barCount: { fontSize: '10px', color: colors.white, fontWeight: 600, marginBottom: '2px', fontFamily: font.family },
  legend: {
    display: 'flex', gap: '16px', alignItems: 'center', marginTop: '12px',
    fontSize: '12px', color: colors.muted, fontFamily: font.family, flexWrap: 'wrap',
  },
  legendItem: { display: 'flex', alignItems: 'center', gap: '6px' },
  legendDot: { width: '10px', height: '10px', borderRadius: '3px', display: 'inline-block' },
}
