// PA-09: Curated Set tab — placeholder for PA-10
import { colors, radii, font } from '../design/tokens'

export default function CuratedSet() {
  return (
    <div style={s.empty}>
      <h3 style={s.title}>No curated set yet</h3>
      <p style={s.text}>
        Browse the Ad Library tab, select your best ads, and build a curated set for export.
      </p>
      <p style={s.hint}>Curation features coming in PA-10.</p>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  empty: {
    textAlign: 'center',
    padding: '60px 20px',
    background: colors.surface,
    borderRadius: radii.card,
  },
  title: { fontSize: '18px', fontWeight: 600, color: colors.white, margin: '0 0 8px', fontFamily: font.family },
  text: { fontSize: '14px', color: colors.muted, margin: '0 0 16px', fontFamily: font.family },
  hint: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
}
