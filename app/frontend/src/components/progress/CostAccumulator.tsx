import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function CostAccumulator({ progress }: { progress: ProgressEvent | null }) {
  const cost = progress?.cost_so_far || 0
  const published = progress?.ads_published || 0
  const costPerAd = published > 0 ? cost / published : 0

  return (
    <div style={s.card}>
      <div style={s.label}>Total Cost</div>
      <div style={s.value}>${cost.toFixed(2)}</div>
      <div style={s.sub}>
        {published > 0 ? `$${costPerAd.toFixed(2)}/published ad` : 'No ads published yet'}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { textAlign: 'center', padding: '20px', background: colors.surface, borderRadius: '16px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family, marginBottom: '4px' },
  value: { fontSize: '32px', fontWeight: 700, color: colors.yellow, fontFamily: font.family },
  sub: { fontSize: '11px', color: colors.muted, fontFamily: font.family, marginTop: '4px' },
}
