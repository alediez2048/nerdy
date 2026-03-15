import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function CycleIndicator({ progress }: { progress: ProgressEvent | null }) {
  const cycle = progress?.cycle || 0
  return (
    <div style={s.card}>
      <div style={s.label}>Cycle</div>
      <div style={s.value}>{cycle}</div>
      <div style={s.sub}>{progress?.type === 'cycle_complete' ? 'Complete' : 'In progress'}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { textAlign: 'center', padding: '20px', background: colors.surface, borderRadius: '16px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family, marginBottom: '4px' },
  value: { fontSize: '36px', fontWeight: 700, color: colors.cyan, fontFamily: font.family },
  sub: { fontSize: '11px', color: colors.muted, fontFamily: font.family },
}
