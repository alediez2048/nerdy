// PA-09: Overview tab — hero metrics + quality trend
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchSummary } from '../api/dashboard'

export default function Overview({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSummary(sessionId).then(setData).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading...</p>

  const summary = (data.pipeline_summary || {}) as Record<string, unknown>

  const metrics = [
    { label: 'Ads Generated', value: summary.total_ads_generated ?? '—' },
    { label: 'Published', value: summary.total_ads_published ?? '—' },
    { label: 'Publish Rate', value: summary.publish_rate ? `${((summary.publish_rate as number) * 100).toFixed(0)}%` : '—' },
    { label: 'Avg Score', value: summary.avg_score ?? '—' },
    { label: 'Total Cost', value: summary.total_cost_usd ? `$${(summary.total_cost_usd as number).toFixed(2)}` : '—' },
    { label: 'Total Tokens', value: summary.total_tokens ? (summary.total_tokens as number).toLocaleString() : '—' },
  ]

  return (
    <div>
      <div style={s.grid}>
        {metrics.map((m) => (
          <div key={m.label} style={s.metricCard}>
            <div style={s.metricValue}>{String(m.value)}</div>
            <div style={s.metricLabel}>{m.label}</div>
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
  },
  metricValue: { fontSize: '24px', fontWeight: 700, color: colors.white, fontFamily: font.family },
  metricLabel: { fontSize: '12px', color: colors.muted, marginTop: '4px', fontFamily: font.family },
}
