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

  return (
    <div>
      {/* Batch score trend */}
      <div style={s.section}>
        <h3 style={s.heading}>Quality Over Batches</h3>
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
        <div style={s.distRow}>
          {distribution.map((count, i) => (
            <div key={i} style={s.distBar}>
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
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: '28px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family },
  chartRow: { display: 'flex', gap: '24px', alignItems: 'flex-start' },
  batchList: { display: 'flex', flexDirection: 'column', gap: '6px' },
  batchItem: { display: 'flex', gap: '12px', fontSize: '13px', fontFamily: font.family },
  distRow: { display: 'flex', gap: '4px', alignItems: 'flex-end', height: '120px' },
  distBar: { flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', textAlign: 'center' },
}
