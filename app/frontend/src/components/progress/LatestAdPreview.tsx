import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function LatestAdPreview({ history }: { history: ProgressEvent[] }) {
  const evals = history.filter((e) => e.type === 'ad_evaluated')
  const latest = evals[evals.length - 1]

  if (!latest) {
    return (
      <div style={s.card}>
        <div style={s.label}>Latest Ad</div>
        <div style={s.empty}>Waiting for evaluations...</div>
      </div>
    )
  }

  const score = latest.current_score_avg || latest.score || 0
  const pass = score >= 7.0
  const color = pass ? colors.mint : score >= 5.5 ? colors.yellow : colors.red

  return (
    <div style={s.card}>
      <div style={s.header}>
        <span style={s.label}>Latest Ad</span>
        <span style={{ ...s.badge, background: `${color}20`, color }}>
          {pass ? 'PASS' : 'BELOW THRESHOLD'}
        </span>
      </div>
      <div style={s.score}>{score.toFixed(1)}</div>
      {latest.copy && <p style={s.copy}>{latest.copy}</p>}
      {latest.ad_id && <span style={s.adId}>{latest.ad_id}</span>}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { padding: '20px', background: colors.surface, borderRadius: '16px' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
  empty: { color: colors.muted, fontSize: '13px', fontFamily: font.family },
  badge: { fontSize: '10px', fontWeight: 600, padding: '2px 8px', borderRadius: '100px', fontFamily: font.family },
  score: { fontSize: '28px', fontWeight: 700, color: colors.white, fontFamily: font.family },
  copy: { fontSize: '13px', color: colors.muted, margin: '8px 0 0', lineHeight: 1.4, fontFamily: font.family },
  adId: { fontSize: '11px', color: colors.muted, fontFamily: font.family },
}
