// PJ-08 — Modal wrapping <Chat touchpoint="refine" />.
//
// First reuse of <Chat /> outside the onboarding flow. Validates that
// the component contract from PJ-07 generalizes: a different touchpoint
// is supplied, the backend's per-touchpoint prompt + whitelist (PJ-05
// + PJ-06) drives a different conversation. No special-case code here.
import { useEffect } from 'react'
import Chat from './Chat'
import { colors, font, radii } from '../design/tokens'

interface Props {
  /** Called whenever the modal should close — on backdrop click, X
      click, or assistant `finish_touchpoint`. The parent re-fetches
      the brand profile so any changes the agent persisted appear in
      the underlying card. */
  onClose: () => void
}

export default function RefineModal({ onClose }: Props) {
  // Lock body scroll while the modal is mounted.
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  // ESC to close.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div
      style={s.backdrop}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div style={s.modal} role="dialog" aria-label="Refine your brand">
        <header style={s.header}>
          <div>
            <h2 style={s.title}>Refine your brand</h2>
            <p style={s.subtitle}>
              Update anything about your business or visual identity. The
              assistant can edit typed fields, add extras, or process a
              new logo upload.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={s.closeBtn}
          >
            ×
          </button>
        </header>
        <div style={s.chatWrap}>
          <Chat
            touchpoint="refine"
            allowUploads={true}
            onCompleted={() => onClose()}
          />
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.6)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2000,
    padding: '24px',
    fontFamily: font.family,
  },
  modal: {
    width: '100%',
    maxWidth: '780px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    background: colors.surface,
    borderRadius: radii.card,
    border: `1px solid ${colors.muted}20`,
    boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '16px',
    padding: '16px 20px',
    borderBottom: `1px solid ${colors.muted}20`,
  },
  title: { color: colors.white, fontSize: '18px', fontWeight: 700, margin: 0 },
  subtitle: { color: colors.muted, fontSize: '12px', margin: '4px 0 0', lineHeight: 1.5 },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    color: colors.muted,
    fontSize: '28px',
    lineHeight: 1,
    cursor: 'pointer',
    padding: '0 4px',
  },
  chatWrap: {
    flex: 1,
    padding: '12px 20px 20px',
    overflow: 'hidden',
    display: 'flex',
  },
}
