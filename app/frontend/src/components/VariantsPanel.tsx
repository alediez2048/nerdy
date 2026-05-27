// VariantsPanel — show all image variants generated for an ad with
// the Pareto-selection rationale. Lazy-loads from
// /api/sessions/{session_id}/ads/{ad_id}/variants on first mount.

import { useEffect, useState } from 'react'
import { colors, font, radii } from '../design/tokens'
import { fetchAdVariants, type AdVariant, type AdVariantsResponse } from '../api/dashboard'

interface Props {
  sessionId: string
  adId: string
}

const VARIANT_LABEL: Record<string, string> = {
  anchor: 'Anchor',
  tone_shift: 'Tone shift',
  composition_shift: 'Composition shift',
}

function describeReason(v: AdVariant): string {
  if (!v.lost_by) return ''
  const { dimension, own_score, winner_score, composite_delta } = v.lost_by
  if (dimension === 'tie') {
    return `Tied — selection went to first variant`
  }
  const dim = dimension === 'attribute' ? 'attribute fit' : 'copy coherence'
  const delta = Math.abs(composite_delta)
  return `Lost on ${dim}: ${own_score.toFixed(2)} vs ${winner_score.toFixed(2)} (composite −${delta.toFixed(3)})`
}

function modelLabel(model: string): string {
  if (model.includes('nano-banana-pro') || model === 'nano-banana-pro-preview') return 'NB Pro'
  if (model.includes('2.5-flash-image') || model.includes('3.1-flash-image')) return 'NB 2'
  return model || 'unknown'
}

export default function VariantsPanel({ sessionId, adId }: Props) {
  const [data, setData] = useState<AdVariantsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    fetchAdVariants(sessionId, adId)
      .then((r) => { if (!cancelled) { setData(r); setLoading(false) } })
      .catch((e) => { if (!cancelled) { setError(e.message); setLoading(false) } })
    return () => { cancelled = true }
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
          No image variants recorded for this ad{error ? ` (${error})` : ''}.
        </p>
      </div>
    )
  }

  const totalCost = data.variants.reduce((acc, v) => acc + v.predicted_cost_usd, 0)

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>
          All {data.variants.length} variants
        </span>
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
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
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
              {!v.is_winner && (
                <p style={styles.reason}>{describeReason(v)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
      <p style={styles.footer}>
        Total spend on this ad's image generations:{' '}
        <strong>${totalCost.toFixed(2)}</strong>
        {' · '}
        Composite weights: attribute fit 40% + copy coherence 60%
      </p>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginTop: '14px',
    padding: '12px',
    borderRadius: radii.md,
    background: 'rgba(0, 240, 255, 0.04)',
    border: `1px solid ${colors.cyan}30`,
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
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: '10px',
  },
  card: {
    borderRadius: radii.sm,
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
    fontFamily: font.body,
    fontSize: '13px',
  },
  metaRow: {
    display: 'flex',
    gap: '6px',
    color: colors.muted,
    fontSize: '11px',
    marginBottom: '2px',
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
}
