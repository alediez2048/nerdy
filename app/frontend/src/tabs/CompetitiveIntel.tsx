// PA-09: Competitive Intel tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCompetitive } from '../api/dashboard'

export default function CompetitiveIntel() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCompetitive().then(setData).catch((e) => setError(e.message))
  }, [])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading competitive intelligence...</p>
  if (Object.keys(data).length === 0) return <p style={{ color: colors.muted }}>No competitive data available</p>

  const hookTypes = (data.hook_type_counts || data.hook_types || {}) as Record<string, number>
  const ctaStyles = (data.cta_style_counts || data.cta_styles || {}) as Record<string, number>
  const angles = (data.emotional_angle_counts || data.emotional_angles || {}) as Record<string, number>

  return (
    <div>
      <FrequencyChart title="Hook Types" data={hookTypes} />
      <FrequencyChart title="CTA Styles" data={ctaStyles} />
      <FrequencyChart title="Emotional Angles" data={angles} />
    </div>
  )
}

function FrequencyChart({ title, data }: { title: string; data: Record<string, number> }) {
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a).slice(0, 10)
  const max = sorted[0]?.[1] || 1

  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={{ fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family }}>
        {title}
      </h3>
      {sorted.map(([label, count]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <span style={{ width: '140px', fontSize: '12px', color: colors.muted, textAlign: 'right', fontFamily: font.family }}>
            {label}
          </span>
          <div style={{ flex: 1, height: '16px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${(count / max) * 100}%`, height: '100%', background: colors.cyan, borderRadius: radii.input }} />
          </div>
          <span style={{ fontSize: '12px', color: colors.white, width: '30px', fontFamily: font.family }}>{count}</span>
        </div>
      ))}
    </div>
  )
}
