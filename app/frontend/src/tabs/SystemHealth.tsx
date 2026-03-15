// PA-09: System Health tab — SPC + confidence + compliance
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchSpc } from '../api/dashboard'

export default function SystemHealth({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSpc(sessionId).then(setData).catch((e) => setError(e.message))
  }, [sessionId])

  if (error) return <p style={{ color: colors.red }}>{error}</p>
  if (!data) return <p style={{ color: colors.muted }}>Loading...</p>

  const health = (data.system_health || {}) as Record<string, unknown>
  const spc = (health.spc || {}) as Record<string, unknown>
  const confidence = (health.confidence_stats || {}) as Record<string, unknown>
  const compliance = (health.compliance_stats || {}) as Record<string, unknown>

  return (
    <div>
      {/* SPC */}
      <div style={s.section}>
        <h3 style={s.heading}>SPC Control Chart</h3>
        <div style={s.row}>
          <Stat label="Mean" value={spc.mean != null ? (spc.mean as number).toFixed(2) : '—'} />
          <Stat label="UCL" value={spc.ucl != null ? (spc.ucl as number).toFixed(2) : '—'} color={colors.red} />
          <Stat label="LCL" value={spc.lcl != null ? (spc.lcl as number).toFixed(2) : '—'} color={colors.yellow} />
          <Stat label="Breaches" value={String((spc.breach_indices as unknown[] || []).length)} color={colors.red} />
        </div>
      </div>

      {/* Confidence */}
      {Object.keys(confidence).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Confidence Routing</h3>
          <div style={s.row}>
            <Stat label="Autonomous" value={`${confidence.autonomous_pct || 0}%`} color={colors.mint} />
            <Stat label="Flagged" value={`${confidence.flagged_pct || 0}%`} color={colors.yellow} />
            <Stat label="Human Required" value={`${confidence.human_required_pct || 0}%`} color={colors.red} />
          </div>
        </div>
      )}

      {/* Compliance */}
      {Object.keys(compliance).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Compliance</h3>
          <div style={s.row}>
            <Stat label="Checked" value={String(compliance.total_checked || 0)} />
            <Stat label="Passed" value={String(compliance.passed || 0)} color={colors.mint} />
            <Stat label="Failed" value={String(compliance.failed || 0)} color={colors.red} />
            <Stat label="Pass Rate" value={compliance.pass_rate ? `${((compliance.pass_rate as number) * 100).toFixed(0)}%` : '—'} />
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '20px', fontWeight: 700, color: color || colors.white, fontFamily: font.family }}>{value}</div>
      <div style={{ fontSize: '11px', color: colors.muted, fontFamily: font.family }}>{label}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  section: { marginBottom: '24px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family },
  row: { display: 'flex', gap: '32px', padding: '16px', background: colors.surface, borderRadius: radii.card },
}
