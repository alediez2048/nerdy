// PA-09: Token Economics tab
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCosts } from '../api/dashboard'

const PRICE_PER_TOKEN = 0.00001

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
  const marginal = (econ.marginal_analysis || {}) as Record<string, unknown>
  const recommendation = (marginal.recommendation || {}) as { max_cycles?: number; reason?: string; savings_tokens?: number }
  const dimBreakdown = (marginal.dimension_breakdown || []) as { dimension: string; cycle_1: number; cycle_2: number; cycle_3: number }[]

  const totalTokens = Object.values(byStage).reduce((a, b) => a + b, 0) || Object.values(byModel).reduce((a, b) => a + b, 0)
  const totalCost = totalTokens * PRICE_PER_TOKEN

  return (
    <div>
      {/* Summary cards */}
      <div style={s.summaryRow}>
        <div style={s.summaryCard}>
          <div style={s.summaryValue}>{totalTokens.toLocaleString()}</div>
          <div style={s.summaryLabel}>Total Tokens</div>
          <div style={s.summarySub}>
            Input + output tokens across all API calls (generation, evaluation, image creation)
          </div>
        </div>
        <div style={s.summaryCard}>
          <div style={{ ...s.summaryValue, color: colors.mint }}>${totalCost.toFixed(2)}</div>
          <div style={s.summaryLabel}>Total Cost</div>
          <div style={s.summarySub}>
            Estimated spend at ~$0.01 per 1K tokens (Gemini Flash pricing)
          </div>
        </div>
        {costPerPub !== undefined && costPerPub > 0 && (
          <div style={s.summaryCard}>
            <div style={{ ...s.summaryValue, color: colors.yellow }}>
              {costPerPub.toLocaleString()} <span style={{ fontSize: '16px', fontWeight: 400 }}>tokens</span>
            </div>
            <div style={s.summaryLabel}>Cost Per Published Ad</div>
            <div style={s.summarySub}>
              ≈ ${(costPerPub * PRICE_PER_TOKEN).toFixed(3)} USD — includes failed attempts and regeneration cycles that didn't publish
            </div>
          </div>
        )}
      </div>

      {/* Cost by stage */}
      <div style={s.section}>
        <h3 style={s.heading}>Cost by Pipeline Stage</h3>
        <p style={s.desc}>
          Where tokens are being spent. <strong>Evaluation</strong> uses tokens for chain-of-thought
          scoring across 5 dimensions. <strong>Generation</strong> creates ad copy from expanded briefs.
          <strong> Routing</strong> decides publish/regenerate/discard. A healthy pipeline spends most
          tokens on evaluation — that's where quality comes from.
        </p>
        <CostBreakdown data={byStage} total={totalTokens} color={colors.yellow} />
      </div>

      {/* Cost by model */}
      <div style={s.section}>
        <h3 style={s.heading}>Cost by Model</h3>
        <p style={s.desc}>
          Token usage per model. <strong>gemini-2.0-flash</strong> handles first-draft generation
          and initial scoring at lowest cost. <strong>gemini-2.5-pro</strong> (if used) targets
          improvable-range ads (5.5–7.0) where quality tokens have the highest ROI.
        </p>
        <CostBreakdown data={byModel} total={totalTokens} color={colors.cyan} />
      </div>

      {/* Marginal analysis */}
      {dimBreakdown.length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Marginal Quality Gains</h3>
          <p style={s.desc}>
            How much each regeneration cycle improves scores by dimension. If a cycle's average
            gain drops below 0.2 points, it's burning tokens without meaningful improvement.
          </p>
          <div style={s.dimGrid}>
            <div style={s.dimHeaderRow}>
              <span style={{ ...s.dimCell, fontWeight: 600 }}>Dimension</span>
              <span style={{ ...s.dimCell, fontWeight: 600 }}>Cycle 1</span>
              <span style={{ ...s.dimCell, fontWeight: 600 }}>Cycle 2</span>
              <span style={{ ...s.dimCell, fontWeight: 600 }}>Cycle 3</span>
            </div>
            {dimBreakdown.map((d) => (
              <div key={d.dimension} style={s.dimRow}>
                <span style={{ ...s.dimCell, color: colors.white }}>{d.dimension.replace(/_/g, ' ')}</span>
                <span style={{ ...s.dimCell, color: gainColor(d.cycle_1) }}>{fmtGain(d.cycle_1)}</span>
                <span style={{ ...s.dimCell, color: gainColor(d.cycle_2) }}>{fmtGain(d.cycle_2)}</span>
                <span style={{ ...s.dimCell, color: gainColor(d.cycle_3) }}>{fmtGain(d.cycle_3)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendation */}
      {recommendation.max_cycles && (
        <div style={s.recoCard}>
          <div style={s.recoTitle}>Pipeline Recommendation</div>
          <p style={s.recoText}>{recommendation.reason}</p>
          {recommendation.savings_tokens !== undefined && recommendation.savings_tokens > 0 && (
            <p style={{ ...s.recoText, color: colors.mint }}>
              Potential savings: {recommendation.savings_tokens.toLocaleString()} tokens
              (${(recommendation.savings_tokens * PRICE_PER_TOKEN).toFixed(2)} USD) per session
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function fmtGain(v: number): string {
  if (v === 0) return '—'
  return `${v > 0 ? '+' : ''}${v.toFixed(2)}`
}

function gainColor(v: number): string {
  if (v === 0) return colors.muted
  if (v >= 0.5) return colors.mint
  if (v >= 0.2) return colors.yellow
  return colors.red
}

function CostBreakdown({ data, total, color }: { data: Record<string, number>; total: number; color: string }) {
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a)
  const max = sorted[0]?.[1] || 1

  return (
    <div>
      {sorted.map(([label, tokens]) => {
        const pct = total > 0 ? ((tokens / total) * 100).toFixed(0) : '0'
        return (
          <div key={label} style={s.barRow}>
            <span style={s.barLabel}>{label}</span>
            <div style={s.barTrack}>
              <div style={{ width: `${(tokens / max) * 100}%`, height: '100%', background: color, borderRadius: '4px' }} />
            </div>
            <span style={s.barValue}>{tokens.toLocaleString()}</span>
            <span style={s.barPct}>{pct}%</span>
          </div>
        )
      })}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  summaryRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '28px' },
  summaryCard: { background: colors.surface, borderRadius: radii.card, padding: '20px', fontFamily: font.family },
  summaryValue: { fontSize: '28px', fontWeight: 700, color: colors.yellow },
  summaryLabel: { fontSize: '13px', color: colors.white, fontWeight: 600, marginTop: '4px' },
  summarySub: { fontSize: '12px', color: colors.muted, marginTop: '6px', lineHeight: 1.4 },
  section: { marginBottom: '32px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 4px', fontFamily: font.family },
  desc: { fontSize: '13px', color: colors.muted, margin: '0 0 14px', lineHeight: 1.5, fontFamily: font.family, maxWidth: '720px' },
  barRow: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' },
  barLabel: { width: '120px', fontSize: '12px', color: colors.muted, textAlign: 'right' as const, fontFamily: font.family },
  barTrack: { flex: 1, height: '20px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' },
  barValue: { fontSize: '12px', color: colors.white, width: '60px', textAlign: 'right' as const, fontFamily: font.family },
  barPct: { fontSize: '11px', color: colors.muted, width: '32px', fontFamily: font.family },
  dimGrid: { fontFamily: font.family },
  dimHeaderRow: { display: 'flex', gap: '4px', padding: '8px 0', borderBottom: `1px solid ${colors.muted}30` },
  dimRow: { display: 'flex', gap: '4px', padding: '6px 0', borderBottom: `1px solid ${colors.muted}10` },
  dimCell: { flex: 1, fontSize: '13px', color: colors.muted },
  recoCard: {
    background: `${colors.cyan}10`, border: `1px solid ${colors.cyan}30`,
    borderRadius: radii.card, padding: '18px', fontFamily: font.family,
  },
  recoTitle: { fontSize: '14px', fontWeight: 600, color: colors.cyan, marginBottom: '6px' },
  recoText: { fontSize: '13px', color: colors.white, margin: '0 0 6px', lineHeight: 1.5 },
}
