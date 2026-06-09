// Settings — BYO API keys.
//
// Each provider has its own card with a password input, Save button,
// and (when set) status row + Remove button. Validation happens
// server-side on save; if the provider rejects the key, the inline
// error is shown and nothing is stored.
import { useCallback, useEffect, useState } from 'react'
import { colors, font, radii } from '../design/tokens'
import { deleteKey, listKeys, saveKey } from '../api/userKeys'
import type { Provider, UserKey } from '../types/userKey'
import useMediaQuery from '../hooks/useMediaQuery'
import BrandProfileCard from '../components/BrandProfileCard'

interface ProviderMeta {
  id: Provider
  name: string
  blurb: string
  signupUrl: string
  required: boolean
}

const PROVIDERS: ProviderMeta[] = [
  {
    id: 'gemini',
    name: 'Google Gemini',
    blurb:
      'Powers text generation, image generation (Nano Banana), and Veo video. Required for every session type.',
    signupUrl: 'https://ai.google.dev/',
    required: true,
  },
  {
    id: 'fal',
    name: 'Fal.ai',
    blurb: 'Default video provider. Add this to run video sessions with provider = fal.',
    signupUrl: 'https://fal.ai/dashboard/keys',
    required: false,
  },
  {
    id: 'kling',
    name: 'Kling',
    blurb: 'Alternative video provider. Add this to run video sessions with provider = kling.',
    signupUrl: 'https://klingai.com/',
    required: false,
  },
]

function formatTime(iso: string | null): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

export default function Settings() {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const [keys, setKeys] = useState<UserKey[]>([])
  const [loading, setLoading] = useState(true)
  const [topError, setTopError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    listKeys()
      .then((rows) => {
        setKeys(rows)
        setTopError(null)
      })
      .catch((e) => setTopError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const byProvider = new Map(keys.map((k) => [k.provider, k]))

  return (
    <div style={s.pageBg}>
      <div style={{ ...s.pageInner, padding: isMobile ? '88px 16px 24px' : s.pageInner.padding }}>
        <h1 style={s.title}>Settings</h1>

        {/* PJ-08: Brand profile — sits above the BYO Keys section so
            users see "this is what AdEngine knows about you" first. */}
        <section style={{ marginBottom: '32px' }}>
          <h2 style={s.sectionHeading}>Brand</h2>
          <BrandProfileCard />
        </section>

        <section>
          <h2 style={s.sectionHeading}>API Keys</h2>
          <p style={s.subtitle}>
            Bring your own API keys. Your keys are encrypted at rest and used only when
            you run sessions. We never log or share them.
          </p>
          {topError && (
            <div style={s.errorBanner}>{topError}</div>
          )}
          {loading ? (
            <p style={{ color: colors.muted }}>Loading…</p>
          ) : (
            <div style={s.providers}>
              {PROVIDERS.map((meta) => (
                <ProviderCard
                  key={meta.id}
                  meta={meta}
                  existing={byProvider.get(meta.id) || null}
                  onChanged={load}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function ProviderCard({
  meta,
  existing,
  onChanged,
}: {
  meta: ProviderMeta
  existing: UserKey | null
  onChanged: () => void
}) {
  const [value, setValue] = useState('')
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSave = async () => {
    if (!value.trim()) {
      setError('Paste your API key first.')
      return
    }
    setBusy(true)
    setError(null)
    try {
      await saveKey(meta.id, value.trim())
      setValue('')
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save key')
    } finally {
      setBusy(false)
    }
  }

  const handleRemove = async () => {
    if (!confirm(`Remove your ${meta.name} key?`)) return
    setBusy(true)
    setError(null)
    try {
      await deleteKey(meta.id)
      onChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to remove key')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={s.card}>
      <div style={s.cardHeader}>
        <div>
          <h2 style={s.providerName}>
            {meta.name}
            {meta.required && <span style={s.requiredBadge}>required</span>}
          </h2>
          <p style={s.providerBlurb}>{meta.blurb}</p>
          <a href={meta.signupUrl} target="_blank" rel="noreferrer" style={s.signupLink}>
            Get a key →
          </a>
        </div>
      </div>
      {existing ? (
        <div style={s.connectedRow}>
          <span style={s.connectedDot}>●</span>
          <span style={{ color: colors.mint, fontWeight: 600, fontSize: '13px' }}>
            Connected
          </span>
          <span style={s.keyMask}>••••••{existing.last_four}</span>
          {existing.validated_at && (
            <span style={s.savedAt}>saved {formatTime(existing.validated_at)}</span>
          )}
          <div style={{ flex: 1 }} />
          <button onClick={handleRemove} disabled={busy} style={s.removeBtn}>
            {busy ? 'Removing…' : 'Remove'}
          </button>
        </div>
      ) : (
        <p style={s.notConfigured}>Not configured.</p>
      )}
      <div style={s.inputRow}>
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={existing ? 'Paste a new key to replace…' : 'Paste your API key…'}
          style={s.input}
          autoComplete="off"
          spellCheck={false}
        />
        <button onClick={() => setShow((s) => !s)} style={s.showBtn}>
          {show ? 'Hide' : 'Show'}
        </button>
        <button onClick={handleSave} disabled={busy || !value} style={s.saveBtn}>
          {busy ? 'Validating…' : existing ? 'Replace' : 'Save'}
        </button>
      </div>
      {error && <div style={s.errorInline}>{error}</div>}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  pageBg: { minHeight: '100vh', width: '100%', background: colors.ink, fontFamily: font.family },
  pageInner: { maxWidth: '900px', margin: '0 auto', padding: '96px 20px 32px' },
  title: { color: colors.white, fontSize: '28px', fontWeight: 700, margin: '0 0 24px' },
  subtitle: { color: colors.muted, fontSize: '14px', margin: '0 0 16px', lineHeight: 1.5 },
  sectionHeading: {
    color: colors.cyan,
    fontSize: '13px',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    margin: '0 0 12px',
    paddingBottom: '6px',
    borderBottom: `1px solid ${colors.muted}20`,
  },
  errorBanner: {
    padding: '10px 14px',
    borderRadius: radii.card,
    background: 'rgba(255, 80, 80, 0.12)',
    border: `1px solid ${colors.red}40`,
    color: colors.red,
    fontSize: '13px',
    marginBottom: '20px',
  },
  providers: { display: 'flex', flexDirection: 'column', gap: '16px' },
  card: {
    background: colors.surface,
    border: `1px solid ${colors.muted}20`,
    borderRadius: radii.card,
    padding: '20px',
  },
  cardHeader: { marginBottom: '14px' },
  providerName: {
    color: colors.white,
    fontSize: '16px',
    fontWeight: 600,
    margin: '0 0 6px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  requiredBadge: {
    padding: '2px 8px',
    borderRadius: '100px',
    background: `${colors.cyan}1f`,
    color: colors.cyan,
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  providerBlurb: { color: colors.muted, fontSize: '13px', margin: '0 0 6px', lineHeight: 1.5 },
  signupLink: { color: colors.cyan, fontSize: '12px', textDecoration: 'none' },
  notConfigured: {
    color: colors.muted,
    fontSize: '13px',
    fontStyle: 'italic',
    margin: '8px 0 12px',
  },
  connectedRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
    padding: '10px 12px',
    background: 'rgba(0, 200, 140, 0.06)',
    border: `1px solid ${colors.mint}30`,
    borderRadius: '6px',
    marginBottom: '12px',
  },
  connectedDot: { color: colors.mint, fontSize: '14px' },
  keyMask: {
    color: colors.white,
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
    fontSize: '13px',
    background: 'rgba(255,255,255,0.04)',
    padding: '2px 8px',
    borderRadius: '4px',
  },
  savedAt: { color: colors.muted, fontSize: '11px' },
  inputRow: { display: 'flex', gap: '8px', flexWrap: 'wrap' },
  input: {
    flex: 1,
    minWidth: '220px',
    padding: '10px 12px',
    border: `1px solid ${colors.muted}40`,
    background: colors.ink,
    color: colors.white,
    borderRadius: radii.button,
    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
    fontSize: '13px',
  },
  showBtn: {
    padding: '10px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontFamily: font.family,
    fontSize: '13px',
  },
  saveBtn: {
    padding: '10px 18px',
    borderRadius: radii.button,
    border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: '#000',
    cursor: 'pointer',
    fontFamily: font.family,
    fontWeight: 700,
    fontSize: '13px',
  },
  removeBtn: {
    padding: '8px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.red}50`,
    background: 'transparent',
    color: colors.red,
    cursor: 'pointer',
    fontFamily: font.family,
    fontSize: '12px',
    fontWeight: 600,
  },
  errorInline: {
    marginTop: '10px',
    padding: '8px 12px',
    borderRadius: '6px',
    background: 'rgba(255, 80, 80, 0.12)',
    border: `1px solid ${colors.red}40`,
    color: colors.red,
    fontSize: '12px',
  },
}
