import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function AdCountBar({ progress, target }: { progress: ProgressEvent | null; target: number }) {
  const generated = progress?.ads_generated || 0
  const published = progress?.ads_published || 0
  const genPct = target > 0 ? Math.min((generated / target) * 100, 100) : 0
  const pubPct = generated > 0 ? Math.min((published / generated) * 100, 100) : 0

  return (
    <div style={s.card}>
      <div style={s.label}>Ads Generated</div>
      <div style={s.barBg}>
        <div style={{ ...s.barFill, width: `${genPct}%`, background: colors.cyan }} />
      </div>
      <div style={s.count}>{generated} / {target}</div>

      <div style={{ ...s.label, marginTop: '12px' }}>Published</div>
      <div style={s.barBg}>
        <div style={{ ...s.barFill, width: `${pubPct}%`, background: colors.mint }} />
      </div>
      <div style={s.count}>{published} / {generated}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { padding: '20px', background: colors.surface, borderRadius: '16px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family, marginBottom: '6px' },
  barBg: { height: '12px', background: `${colors.muted}20`, borderRadius: '6px', overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: '6px', transition: 'width 0.3s ease' },
  count: { fontSize: '13px', color: colors.white, fontFamily: font.family, marginTop: '4px', fontWeight: 600 },
}
