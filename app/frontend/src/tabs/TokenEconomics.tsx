// PA-09: Token Economics tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCosts } from '../api/dashboard'

export default function TokenEconomics({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCosts(sessionId).then(setData).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading...</p>

  const econ = (data.token_economics || {}) as Record<string, unknown>
  const byStage = (econ.by_stage || {}) as Record<string, number>
  const byModel = (econ.by_model || {}) as Record<string, number>
  const costPerPub = econ.cost_per_published as number | undefined

  return (
    <div>
      {/* Cost per published ad */}
      {costPerPub !== undefined && (
        <div style={s.hero}>
          <div style={s.heroValue}>${costPerPub.toFixed(2)}</div>
          <div style={s.heroLabel}>Cost Per Published Ad</div>
        </div>
      )}

      {/* By stage */}
      <div style={s.section}>
        <h3 style={s.heading}>Cost by Pipeline Stage</h3>
        <CostBreakdown data={byStage} />
      </div>

      {/* By model */}
      <div style={s.section}>
        <h3 style={s.heading}>Cost by Model</h3>
        <CostBreakdown data={byModel} />
      </div>
    </div>
  )
}

function CostBreakdown({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a)

  return (
    <div>
      {sorted.map(([label, tokens]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span style={{ width: '120px', fontSize: '12px', color: colors.muted, textAlign: 'right', fontFamily: font.family }}>
            {label}
          </span>
          <div style={{ flex: 1, height: '20px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${(tokens / total) * 100}%`, height: '100%', background: colors.yellow, borderRadius: radii.input }} />
          </div>
          <span style={{ fontSize: '12px', color: colors.white, width: '60px', fontFamily: font.family }}>
            {tokens.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  hero: { textAlign: 'center', padding: '24px', background: colors.surface, borderRadius: radii.card, marginBottom: '24px' },
  heroValue: { fontSize: '36px', fontWeight: 700, color: colors.yellow, fontFamily: font.family },
  heroLabel: { fontSize: '14px', color: colors.muted, fontFamily: font.family },
  section: { marginBottom: '24px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family },
}
