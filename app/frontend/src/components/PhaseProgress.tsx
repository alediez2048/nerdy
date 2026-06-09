// PJ-07 — 5-dot onboarding progress bar.
import { colors, font } from '../design/tokens'
import type { Phase } from '../types/agent'

interface Props {
  phase: Phase
  /** Optional click handler for dots. When supplied, dots render as
      buttons and clicks invoke the handler with the clicked phase —
      used by Settings (PJ-08 §7.6) to open the refine modal scoped to
      a specific phase. */
  onDotClick?: (phase: Phase) => void
}

const STEPS: { key: Phase; label: string }[] = [
  { key: 'identify', label: 'Identify' },
  { key: 'core', label: 'Core' },
  { key: 'extras', label: 'Extras' },
  { key: 'assets', label: 'Assets' },
  { key: 'good_enough', label: 'Ready' },
]

function indexFor(phase: Phase): number {
  // "complete" treats the bar as fully filled.
  if (phase === 'complete') return STEPS.length
  const i = STEPS.findIndex((s) => s.key === phase)
  return i < 0 ? 0 : i
}

export default function PhaseProgress({ phase, onDotClick }: Props) {
  const currentIdx = indexFor(phase)
  const interactive = typeof onDotClick === 'function'

  return (
    <div style={s.wrap}>
      <div style={s.row}>
        {STEPS.map((step, i) => {
          const reached = i <= currentIdx
          const isCurrent = i === currentIdx && phase !== 'complete'
          const dotEl = (
            <div
              style={{
                ...s.dot,
                background: reached ? colors.cyan : `${colors.muted}40`,
                boxShadow: isCurrent ? `0 0 12px ${colors.cyan}80` : 'none',
                transform: isCurrent ? 'scale(1.25)' : 'scale(1)',
                cursor: interactive ? 'pointer' : 'default',
              }}
              aria-current={isCurrent ? 'step' : undefined}
            />
          )
          return (
            <div key={step.key} style={s.stepWrap}>
              {interactive ? (
                <button
                  type="button"
                  onClick={() => onDotClick?.(step.key)}
                  style={s.dotBtn}
                  aria-label={`Refine ${step.label}`}
                >
                  {dotEl}
                </button>
              ) : (
                dotEl
              )}
              <span
                style={{
                  ...s.label,
                  color: reached ? colors.cyan : colors.muted,
                  fontWeight: isCurrent ? 700 : 500,
                }}
              >
                {step.label}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  style={{
                    ...s.connector,
                    background: i < currentIdx ? colors.cyan : `${colors.muted}30`,
                  }}
                />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  wrap: {
    padding: '12px 0 18px',
    fontFamily: font.family,
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '8px',
  },
  stepWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: 1,
  },
  dot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    flexShrink: 0,
    transition: 'transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease',
  },
  dotBtn: {
    background: 'transparent',
    border: 'none',
    padding: '4px',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: '12px',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    transition: 'color 0.2s ease',
  },
  connector: {
    flex: 1,
    height: '1px',
    transition: 'background 0.2s ease',
  },
}
