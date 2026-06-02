// VariantsPanel — show all variants generated for an ad with selection
// rationale. PI-08: branches on schema_version. v2 shape renders an
// Evidence panel with per-dimension scores + rationales; v1 (legacy)
// keeps the original attribute/coherence layout under a "Legacy
// scoring" badge.

import { useEffect, useState } from 'react'
import { colors, font, radii } from '../design/tokens'
import {
  fetchAdVariants,
  type AdVariant,
  type AdVariantV2,
  type AdVariantsResponse,
  type AdVariantsV2Response,
  type AnyVariantsResponse,
} from '../api/dashboard'

interface Props {
  sessionId: string
  adId: string
}

const VARIANT_LABEL: Record<string, string> = {
  anchor: 'Anchor',
  tone_shift: 'Tone shift',
  composition_shift: 'Composition shift',
  alternative: 'Alternative',
}

function modelLabel(model: string): string {
  if (model.includes('nano-banana-pro') || model === 'nano-banana-pro-preview') return 'NB Pro'
  if (model.includes('2.5-flash-image') || model.includes('3.1-flash-image')) return 'NB 2'
  return model || 'unknown'
}

function isV2(data: AnyVariantsResponse): data is AdVariantsV2Response {
  return data.schema_version === 'v2'
}

// --- v1 (legacy) helpers --------------------------------------------------

function describeReasonV1(v: AdVariant): string {
  if (!v.lost_by) return ''
  const { dimension, own_score, winner_score, composite_delta } = v.lost_by
  if (dimension === 'tie') return 'Tied — selection went to first variant'
  const dim = dimension === 'attribute' ? 'attribute fit' : 'copy coherence'
  const delta = Math.abs(composite_delta)
  return `Lost on ${dim}: ${own_score.toFixed(2)} vs ${winner_score.toFixed(2)} (composite −${delta.toFixed(3)})`
}

// --- v2 helpers -----------------------------------------------------------

function describeWinnerReason(reason: AdVariantsV2Response['winner_reason']): string {
  if (!reason || !reason.distinguishing_dimensions.length) return ''
  const dims = reason.distinguishing_dimensions
    .map((d) => {
      if (d.delta_vs_mean != null) {
        const sign = d.delta_vs_mean >= 0 ? '+' : ''
        return `${d.dimension} ${sign}${d.delta_vs_mean.toFixed(1)}`
      }
      if (d.absolute_score != null) return `${d.dimension} (score ${d.absolute_score})`
      return d.dimension
    })
    .join(', ')
  return `Why this won — ${dims}`
}

function describeRejectionV2(v: AdVariantV2): string {
  if (!v.rejection_reason) return ''
  const r = v.rejection_reason
  const sign = r.worst_dimension_delta >= 0 ? '+' : ''
  return `Lost on ${r.worst_dimension}: ${sign}${r.worst_dimension_delta.toFixed(1)} (composite ${r.composite_delta.toFixed(1)}). ${r.worst_dimension_rationale}`
}

function EvidencePanel({ variant }: { variant: AdVariantV2 }) {
  const [open, setOpen] = useState(false)
  const triggeredGates = Object.entries(variant.penalty_gates).filter(([, g]) => g.triggered)
  return (
    <div style={{ marginTop: '8px' }}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={styles.expander}
      >
        {open ? '▾' : '▸'} Evidence ({Object.keys(variant.dimensions).length} dims
        {triggeredGates.length ? `, ${triggeredGates.length} gates` : ''})
      </button>
      {open && (
        <div style={styles.evidence}>
          <table style={styles.evidenceTable}>
            <thead>
              <tr>
                <th style={styles.evidenceTh}>Dimension</th>
                <th style={styles.evidenceTh}>Score</th>
                <th style={styles.evidenceTh}>Weight</th>
                <th style={styles.evidenceTh}>Rationale</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(variant.dimensions).map(([name, d]) => (
                <tr key={name}>
                  <td style={styles.evidenceTd}>{name}</td>
                  <td style={styles.evidenceTd}>{d.score}/10</td>
                  <td style={styles.evidenceTd}>{(d.weight * 100).toFixed(0)}%</td>
                  <td style={{ ...styles.evidenceTd, fontStyle: 'italic' }}>{d.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {triggeredGates.length > 0 && (
            <div style={{ marginTop: '8px', color: colors.red, fontSize: '11px' }}>
              <strong>Triggered penalty gates:</strong>
              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                {triggeredGates.map(([name, g]) => (
                  <li key={name}>
                    {name} — <span style={{ fontStyle: 'italic' }}>{g.rationale}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div style={{ marginTop: '8px', color: colors.muted, fontSize: '11px' }}>
            raw {variant.raw_score.toFixed(2)} × penalty {variant.penalty_multiplier.toFixed(2)} = composite{' '}
            {variant.composite_score.toFixed(1)}
          </div>
        </div>
      )}
    </div>
  )
}

// --- Component ------------------------------------------------------------

export default function VariantsPanel({ sessionId, adId }: Props) {
  const [data, setData] = useState<AnyVariantsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchAdVariants(sessionId, adId)
      .then((r) => {
        if (!cancelled) {
          setData(r)
          setLoading(false)
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message)
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [sessionId, adId])

  if (loading) {
    return (
      <div style={styles.container}>
        <p style={styles.muted}>Loading variants…</p>
      </div>
    )
  }
  if (error || !data) {
    return (
      <div style={styles.container}>
        <p style={styles.muted}>
          No variants recorded for this ad{error ? ` (${error})` : ''}.
        </p>
      </div>
    )
  }

  return isV2(data) ? renderV2(data) : renderV1(data)
}

function renderV1(data: AdVariantsResponse) {
  const totalCost = data.variants.reduce((acc, v) => acc + v.predicted_cost_usd, 0)
  return (
    <div style={styles.container}>
      <div style={styles.legacyBadge}>
        Legacy scoring (pre-2026-05-15) — per-dimension breakdown not available for this
        session.
      </div>
      <div style={styles.header}>
        <span style={styles.title}>All {data.variants.length} variants</span>
        <span style={styles.muted}>
          Selection: <code>{data.selection_criteria.formula}</code>
        </span>
      </div>
      <div style={styles.grid}>
        {data.variants.map((v) => (
          <div
            key={v.variant_type}
            style={{
              ...styles.card,
              border: v.is_winner
                ? `2px solid ${colors.mint}`
                : `1px solid ${colors.muted}30`,
            }}
          >
            {v.image_url ? (
              <img
                src={v.image_url}
                alt={`${v.variant_type} variant`}
                style={styles.thumb}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : (
              <div style={{ ...styles.thumb, ...styles.placeholder }}>
                <span style={{ fontSize: '24px' }}>🖼️</span>
              </div>
            )}
            <div style={styles.body}>
              <div style={styles.row}>
                <strong style={{ color: colors.white }}>
                  {VARIANT_LABEL[v.variant_type] || v.variant_type}
                </strong>
                {v.is_winner ? (
                  <span style={styles.winnerBadge}>✓ Selected</span>
                ) : (
                  <span style={styles.score}>{v.composite_score.toFixed(2)}</span>
                )}
              </div>
              <div style={styles.metaRow}>
                <span>attr {v.attribute_pass_pct.toFixed(2)}</span>
                <span>·</span>
                <span>coh {v.coherence_avg.toFixed(2)}</span>
              </div>
              <div style={styles.metaRow}>
                <span>{modelLabel(v.model_used)}</span>
                <span>·</span>
                <span>${v.predicted_cost_usd.toFixed(3)}</span>
              </div>
              {!v.is_winner && <p style={styles.reason}>{describeReasonV1(v)}</p>}
            </div>
          </div>
        ))}
      </div>
      <p style={styles.footer}>
        Total spend on this ad's image generations: <strong>${totalCost.toFixed(2)}</strong>
        {' · '}
        Composite weights: attribute fit 40% + copy coherence 60%
      </p>
    </div>
  )
}

function renderV2(data: AdVariantsV2Response) {
  const totalCost = data.variants.reduce((acc, v) => acc + v.predicted_cost_usd, 0)
  const winnerLine = describeWinnerReason(data.winner_reason)
  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>All {data.variants.length} variants</span>
        <span style={styles.muted}>
          Selection: <code>{data.selection_criteria.formula}</code>
        </span>
      </div>
      <div style={styles.grid}>
        {data.variants.map((v) => (
          <div
            key={v.variant_type}
            style={{
              ...styles.card,
              border: v.is_winner
                ? `2px solid ${colors.mint}`
                : `1px solid ${colors.muted}30`,
            }}
          >
            {v.image_url ? (
              <img
                src={v.image_url}
                alt={`${v.variant_type} variant`}
                style={styles.thumb}
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            ) : (
              <div style={{ ...styles.thumb, ...styles.placeholder }}>
                <span style={{ fontSize: '24px' }}>
                  {v.media_type === 'video' ? '🎬' : '🖼️'}
                </span>
              </div>
            )}
            <div style={styles.body}>
              <div style={styles.row}>
                <strong style={{ color: colors.white }}>
                  {VARIANT_LABEL[v.variant_type] || v.variant_type}
                </strong>
                {v.is_winner ? (
                  <span style={styles.winnerBadge}>✓ Selected</span>
                ) : (
                  <span style={styles.score}>{v.composite_score.toFixed(1)}</span>
                )}
              </div>
              <div style={styles.metaRow}>
                <span>{modelLabel(v.model_used)}</span>
                <span>·</span>
                <span>${v.predicted_cost_usd.toFixed(3)}</span>
                <span>·</span>
                <span>{v.media_type}</span>
              </div>
              {v.is_winner && winnerLine && <p style={styles.reason}>{winnerLine}</p>}
              {!v.is_winner && v.rejection_reason && (
                <p style={styles.reason}>{describeRejectionV2(v)}</p>
              )}
              <EvidencePanel variant={v} />
            </div>
          </div>
        ))}
      </div>
      <p style={styles.footer}>
        Total spend on this ad's variant generations:{' '}
        <strong>${totalCost.toFixed(2)}</strong>
      </p>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '14px',
    padding: '12px',
    borderRadius: '8px',
    background: 'rgba(0, 240, 255, 0.04)',
    border: `1px solid ${colors.cyan}30`,
  },
  legacyBadge: {
    color: colors.muted,
    fontStyle: 'italic',
    fontSize: '11px',
    marginBottom: '10px',
    padding: '6px 8px',
    background: 'rgba(255,255,255,0.03)',
    borderRadius: '4px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
    gap: '8px',
    flexWrap: 'wrap',
  },
  title: { color: colors.cyan, fontSize: '13px', fontWeight: 600 },
  muted: { color: colors.muted, fontSize: '11px', margin: 0 },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '10px',
  },
  card: {
    borderRadius: '8px',
    overflow: 'hidden',
    background: 'rgba(0,0,0,0.25)',
    display: 'flex',
    flexDirection: 'column',
  },
  thumb: {
    width: '100%',
    aspectRatio: '1 / 1',
    objectFit: 'cover' as const,
    background: '#000',
  },
  placeholder: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: colors.muted,
  },
  body: { padding: '8px 10px' },
  row: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
    fontFamily: font.family,
    fontSize: '13px',
  },
  metaRow: {
    display: 'flex',
    gap: '6px',
    color: colors.muted,
    fontSize: '11px',
    marginBottom: '2px',
    flexWrap: 'wrap' as const,
  },
  winnerBadge: {
    background: colors.mint,
    color: '#000',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 700,
  },
  score: {
    color: colors.yellow,
    fontWeight: 600,
    fontSize: '12px',
  },
  reason: {
    color: colors.muted,
    fontSize: '11px',
    margin: '6px 0 0',
    lineHeight: 1.4,
    fontStyle: 'italic',
  },
  footer: {
    color: colors.muted,
    fontSize: '11px',
    margin: '10px 0 0',
    lineHeight: 1.5,
  },
  expander: {
    fontSize: '11px',
    background: 'transparent',
    color: colors.cyan,
    border: 'none',
    cursor: 'pointer',
    padding: '4px 0',
    textAlign: 'left' as const,
  },
  evidence: {
    marginTop: '6px',
    padding: '8px',
    background: 'rgba(0,0,0,0.35)',
    borderRadius: '4px',
  },
  evidenceTable: {
    width: '100%',
    fontSize: '11px',
    color: colors.white,
    borderCollapse: 'collapse' as const,
  },
  evidenceTh: {
    textAlign: 'left' as const,
    color: colors.muted,
    fontWeight: 500,
    fontSize: '10px',
    padding: '2px 4px',
    borderBottom: `1px solid ${colors.muted}30`,
  },
  evidenceTd: {
    padding: '3px 4px',
    verticalAlign: 'top' as const,
    borderBottom: `1px solid ${colors.muted}15`,
  },
}

// `radii` is intentionally unused in v2 styles (component uses inline values
// to avoid relying on tokens that aren't part of the design system yet).
void radii