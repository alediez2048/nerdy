// PJ-08 — Settings "Brand Profile" card.
//
// Reads /api/me/brand-profile, renders typed-core summary + extras
// viewer + 5-dot progress (clickable post-onboarding) + a "Refine your
// brand" button. The button (and every dot post-onboarding) opens a
// modal wrapping <Chat touchpoint="refine" />. On modal close the card
// re-fetches so any agent-persisted changes appear immediately.
import { useCallback, useEffect, useState } from 'react'
import { getBrandProfile, type BrandProfileFull } from '../api/brandProfile'
import { colors, font, radii } from '../design/tokens'
import PhaseProgress from './PhaseProgress'
import RefineModal from './RefineModal'

export default function BrandProfileCard() {
  const [profile, setProfile] = useState<BrandProfileFull | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refineOpen, setRefineOpen] = useState(false)
  const [extrasOpen, setExtrasOpen] = useState(false)

  const load = useCallback(() => {
    setLoading(true)
    getBrandProfile()
      .then((p) => {
        setProfile(p)
        setError(null)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div style={s.card}>
        <p style={s.muted}>Loading brand profile…</p>
      </div>
    )
  }
  if (error) {
    return (
      <div style={s.card}>
        <p style={s.error}>{error}</p>
      </div>
    )
  }
  if (!profile) {
    // No brand_profile row → onboarding hasn't happened yet.
    return (
      <div style={s.card}>
        <h2 style={s.title}>Brand Profile</h2>
        <p style={s.muted}>
          You haven't set up your brand yet. The onboarding wizard will
          guide you through it.
        </p>
        <a href="/onboarding" style={s.cta}>
          Start onboarding →
        </a>
      </div>
    )
  }

  const extrasKeys = Object.keys(profile.extras)
  const paletteHexes = [
    profile.palette_primary_hex,
    profile.palette_secondary_hex,
    profile.palette_accent_hex,
  ].filter((h): h is string => !!h)

  const closeRefine = () => {
    setRefineOpen(false)
    load()
  }

  return (
    <div style={s.card}>
      <header style={s.header}>
        <div>
          <h2 style={s.title}>{profile.business_name || 'Brand Profile'}</h2>
          {profile.industry && (
            <span style={s.industryBadge}>{profile.industry}</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => setRefineOpen(true)}
          style={s.refineBtn}
        >
          Refine your brand
        </button>
      </header>

      <PhaseProgress
        phase={profile.onboarding_phase}
        onDotClick={() => setRefineOpen(true)}
      />

      <div style={s.fieldGrid}>
        <Field label="Audience">{profile.audience || em('not set')}</Field>
        <Field label="Mission" wide>
          {profile.mission || em('not set')}
        </Field>
        <Field label="Value props" wide>
          <Chips items={profile.value_props} />
        </Field>
        <Field label="Tone">
          <Chips items={profile.tone_descriptors} />
        </Field>
        {profile.avoid_phrases.length > 0 && (
          <Field label="Avoid phrases">
            <Chips items={profile.avoid_phrases} variant="warn" />
          </Field>
        )}
      </div>

      {profile.do_dont_rules &&
        (profile.do_dont_rules.do.length > 0 ||
          profile.do_dont_rules.dont.length > 0) && (
          <div style={s.doDontWrap}>
            <DoDontColumn
              label="Do"
              items={profile.do_dont_rules.do}
              accent={colors.mint}
            />
            <DoDontColumn
              label="Don't"
              items={profile.do_dont_rules.dont}
              accent={colors.red}
            />
          </div>
        )}

      {(paletteHexes.length > 0 || profile.logo_asset_url) && (
        <div style={s.visualRow}>
          {profile.logo_asset_url && (
            <div style={s.logoBlock}>
              <span style={s.fieldLabel}>Logo</span>
              <img
                src={`${import.meta.env.DEV ? 'http://localhost:8000' : ''}${profile.logo_asset_url}`}
                alt="Brand logo"
                style={s.logoImg}
                onError={(e) => {
                  ;(e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            </div>
          )}
          {paletteHexes.length > 0 && (
            <div style={s.paletteBlock}>
              <span style={s.fieldLabel}>Palette</span>
              <div style={s.swatchRow}>
                {paletteHexes.map((hex) => (
                  <div
                    key={hex}
                    title={hex}
                    style={{ ...s.swatch, background: hex }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        type="button"
        style={s.extrasHeader}
        onClick={() => setExtrasOpen((v) => !v)}
        aria-expanded={extrasOpen}
      >
        Extras ({extrasKeys.length}) {extrasOpen ? '▾' : '▸'}
      </button>
      {extrasOpen && (
        <div style={s.extrasBody}>
          {extrasKeys.length === 0 ? (
            <p style={s.muted}>No extras yet. Refine your brand to add some.</p>
          ) : (
            extrasKeys.map((k) => (
              <div key={k} style={s.extrasRow}>
                <span style={s.extrasKey}>{k}</span>
                <code style={s.extrasValue}>
                  {formatExtraValue(profile.extras[k])}
                </code>
              </div>
            ))
          )}
        </div>
      )}

      {refineOpen && <RefineModal onClose={closeRefine} />}
    </div>
  )
}

// --- Subcomponents -----------------------------------------------

function Field({
  label,
  wide,
  children,
}: {
  label: string
  wide?: boolean
  children: React.ReactNode
}) {
  return (
    <div style={{ gridColumn: wide ? 'span 2' : 'span 1' }}>
      <span style={s.fieldLabel}>{label}</span>
      <div style={s.fieldValue}>{children}</div>
    </div>
  )
}

function Chips({
  items,
  variant = 'default',
}: {
  items: string[]
  variant?: 'default' | 'warn'
}) {
  if (!items || items.length === 0) return em('not set')
  return (
    <div style={s.chipRow}>
      {items.map((it) => (
        <span
          key={it}
          style={{
            ...s.chip,
            background:
              variant === 'warn' ? `${colors.red}1f` : `${colors.cyan}1f`,
            color: variant === 'warn' ? colors.red : colors.cyan,
            border: `1px solid ${
              variant === 'warn' ? colors.red : colors.cyan
            }30`,
          }}
        >
          {it}
        </span>
      ))}
    </div>
  )
}

function DoDontColumn({
  label,
  items,
  accent,
}: {
  label: string
  items: string[]
  accent: string
}) {
  return (
    <div style={s.doDontCol}>
      <span style={{ ...s.fieldLabel, color: accent, fontWeight: 700 }}>
        {label}
      </span>
      <ul style={s.doDontList}>
        {items.length === 0 ? (
          <li style={s.muted}>(none)</li>
        ) : (
          items.map((it, i) => (
            <li key={i} style={{ color: colors.white, fontSize: '13px' }}>
              {it}
            </li>
          ))
        )}
      </ul>
    </div>
  )
}

function em(text: string) {
  return <em style={s.muted}>{text}</em>
}

function formatExtraValue(v: unknown): string {
  if (v == null) return 'null'
  if (typeof v === 'string') return v
  if (Array.isArray(v) || typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

// --- Styles ------------------------------------------------------

const s: Record<string, React.CSSProperties> = {
  card: {
    background: colors.surface,
    border: `1px solid ${colors.muted}20`,
    borderRadius: radii.card,
    padding: '20px',
    fontFamily: font.family,
    marginBottom: '16px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
    marginBottom: '8px',
  },
  title: {
    color: colors.white,
    fontSize: '18px',
    fontWeight: 700,
    margin: 0,
  },
  industryBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '100px',
    background: `${colors.cyan}1f`,
    color: colors.cyan,
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginTop: '6px',
  },
  refineBtn: {
    padding: '8px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}10`,
    color: colors.cyan,
    cursor: 'pointer',
    fontFamily: font.family,
    fontWeight: 600,
    fontSize: '12px',
    flexShrink: 0,
  },
  cta: {
    color: colors.cyan,
    fontSize: '13px',
    textDecoration: 'none',
    display: 'inline-block',
    marginTop: '6px',
  },
  fieldGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
    margin: '12px 0',
  },
  fieldLabel: {
    color: colors.muted,
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    display: 'block',
    marginBottom: '4px',
  },
  fieldValue: {
    color: colors.white,
    fontSize: '13px',
    lineHeight: 1.5,
  },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: '6px' },
  chip: {
    padding: '3px 10px',
    borderRadius: '100px',
    fontSize: '12px',
    fontWeight: 500,
  },
  doDontWrap: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '14px',
    margin: '8px 0 14px',
    padding: '12px',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: radii.button,
  },
  doDontCol: { display: 'flex', flexDirection: 'column' },
  doDontList: { margin: '4px 0 0', paddingLeft: '16px', listStyle: 'disc' },
  visualRow: {
    display: 'flex',
    gap: '20px',
    margin: '8px 0 14px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  logoBlock: { display: 'flex', flexDirection: 'column', gap: '6px' },
  logoImg: {
    width: '80px',
    height: '80px',
    objectFit: 'contain',
    background: colors.ink,
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}30`,
  },
  paletteBlock: { display: 'flex', flexDirection: 'column', gap: '6px' },
  swatchRow: { display: 'flex', gap: '8px' },
  swatch: {
    width: '40px',
    height: '40px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
  },
  extrasHeader: {
    background: 'transparent',
    border: 'none',
    color: colors.cyan,
    fontFamily: font.family,
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
    padding: '8px 0',
    textAlign: 'left',
    marginTop: '8px',
    display: 'block',
    width: '100%',
  },
  extrasBody: {
    padding: '8px 12px',
    background: 'rgba(0,0,0,0.2)',
    borderRadius: radii.button,
    border: `1px dashed ${colors.muted}30`,
  },
  extrasRow: {
    display: 'flex',
    gap: '12px',
    padding: '6px 0',
    borderBottom: `1px solid ${colors.muted}10`,
    alignItems: 'baseline',
  },
  extrasKey: {
    color: colors.cyan,
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
    fontSize: '12px',
    minWidth: '160px',
  },
  extrasValue: {
    color: colors.white,
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
    fontSize: '12px',
    wordBreak: 'break-all',
    flex: 1,
  },
  muted: { color: colors.muted, fontStyle: 'italic', fontSize: '13px' },
  error: { color: colors.red, fontSize: '13px' },
}
