import { useRef, useEffect } from 'react'
import { colors, font } from '../../design/tokens'
import type { ProgressEvent } from '../../types/progress'

export default function ScoreFeed({ history }: { history: ProgressEvent[] }) {
  const listRef = useRef<HTMLDivElement>(null)
  const evals = history.filter((e) => e.type === 'ad_evaluated')
  const recent = evals.slice(-15)

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight
  }, [recent.length])

  return (
    <div style={s.card}>
      <div style={s.label}>Live Score Feed</div>
      <div ref={listRef} style={s.list}>
        {recent.length === 0 ? (
          <div style={s.empty}>Waiting for evaluations...</div>
        ) : (
          recent.map((e, i) => {
            const score = e.current_score_avg || e.score || 0
            const color = score >= 7 ? colors.mint : score >= 5.5 ? colors.yellow : colors.red
            return (
              <div key={i} style={s.item}>
                <span style={s.idx}>#{e.ads_evaluated}</span>
                <span style={{ ...s.score, color }}>{score.toFixed(1)}</span>
                <span style={{ ...s.badge, background: `${color}20`, color }}>
                  {score >= 7 ? 'PASS' : score >= 5.5 ? 'IMPROVE' : 'FAIL'}
                </span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: { padding: '20px', background: colors.surface, borderRadius: '16px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family, marginBottom: '8px' },
  list: { maxHeight: '200px', overflowY: 'auto' },
  empty: { color: colors.muted, fontSize: '13px', fontFamily: font.family },
  item: { display: 'flex', alignItems: 'center', gap: '10px', padding: '4px 0', borderBottom: `1px solid ${colors.muted}15` },
  idx: { fontSize: '11px', color: colors.muted, fontFamily: font.family, width: '30px' },
  score: { fontSize: '16px', fontWeight: 700, fontFamily: font.family },
  badge: { fontSize: '10px', fontWeight: 600, padding: '2px 8px', borderRadius: '100px', fontFamily: font.family },
}
