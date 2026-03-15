import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function QualityTrend({ history }: { history: ProgressEvent[] }) {
  const points = history
    .filter((e) => e.type === 'ad_evaluated' || e.type === 'cycle_complete')
    .map((e) => e.current_score_avg)
    .filter((v) => v > 0)

  if (points.length < 2) {
    return (
      <div style={s.card}>
        <div style={s.label}>Quality Trend</div>
        <div style={s.empty}>Collecting data...</div>
      </div>
    )
  }

  const W = 280, H = 80, PAD = 4
  const min = Math.min(...points, 5)
  const max = Math.max(...points, 9)
  const range = max - min || 1

  const svgPoints = points.map((val, i) => {
    const x = PAD + (i / (points.length - 1)) * (W - PAD * 2)
    const y = PAD + (1 - (val - min) / range) * (H - PAD * 2)
    return `${x},${y}`
  }).join(' ')

  // Threshold line at 7.0
  const threshY = PAD + (1 - (7.0 - min) / range) * (H - PAD * 2)

  return (
    <div style={s.card}>
      <div style={s.label}>Quality Trend</div>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        {/* Threshold line */}
        <line x1={0} y1={threshY} x2={W} y2={threshY} stroke={colors.muted} strokeWidth={1} strokeDasharray="4 4" opacity={0.5} />
        {/* Score line */}
        <polyline fill="none" stroke={colors.cyan} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" points={svgPoints} />
      </svg>
      <div style={s.legend}>
        <span style={{ color: colors.cyan, fontSize: '11px' }}>Score avg</span>
        <span style={{ color: colors.muted, fontSize: '11px' }}>— 7.0 threshold</span>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { padding: '20px', background: colors.surface, borderRadius: '16px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family, marginBottom: '8px' },
  empty: { color: colors.muted, fontSize: '13px', fontFamily: font.family },
  legend: { display: 'flex', gap: '16px', marginTop: '4px', fontFamily: font.family },
}
