// PA-11: Share button + modal
import { useState } from 'react'
import { colors, radii, font } from '../design/tokens'

import { getAuthTokenSync } from '../api/auth'

const BASE = '/api/sessions'

function getHeaders(): HeadersInit {
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  const token = getAuthTokenSync()
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export default function ShareButton({ sessionId }: { sessionId: string }) {
  const [showModal, setShowModal] = useState(false)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [expiresAt, setExpiresAt] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleShare = async () => {
    setLoading(true)
    try {
      const resp = await fetch(`${BASE}/${sessionId}/share`, {
        method: 'POST',
        headers: getHeaders(),
      })
      if (!resp.ok) throw new Error('Failed to create share link')
      const data = await resp.json()
      setShareUrl(data.share_url)
      setExpiresAt(data.expires_at)
      setShowModal(true)
    } catch {
      // Silently fail
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleRevoke = async () => {
    await fetch(`${BASE}/${sessionId}/share`, {
      method: 'DELETE',
      headers: getHeaders(),
    })
    setShowModal(false)
    setShareUrl(null)
  }

  return (
    <>
      <button onClick={handleShare} disabled={loading} style={s.btn}>
        {loading ? '...' : 'Share'}
      </button>

      {showModal && (
        <div style={s.overlay} onClick={() => setShowModal(false)}>
          <div style={s.modal} onClick={(e) => e.stopPropagation()}>
            <h3 style={s.title}>Share Session</h3>
            <p style={s.text}>Anyone with this link can view (read-only) for 7 days.</p>

            <div style={s.urlRow}>
              <input type="text" value={shareUrl || ''} readOnly style={s.urlInput} />
              <button onClick={handleCopy} style={s.copyBtn}>
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>

            {expiresAt && (
              <p style={s.expiry}>Expires: {new Date(expiresAt).toLocaleDateString()}</p>
            )}

            <button onClick={handleRevoke} style={s.revokeBtn}>Revoke Link</button>
          </div>
        </div>
      )}
    </>
  )
}

const s: Record<string, React.CSSProperties> = {
  btn: {
    padding: '8px 18px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.white, cursor: 'pointer', fontSize: '13px', fontFamily: font.family,
  },
  overlay: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000,
  },
  modal: {
    background: colors.surface, borderRadius: radii.card, padding: '32px',
    width: '100%', maxWidth: '450px', fontFamily: font.family,
  },
  title: { fontSize: '18px', fontWeight: 600, color: colors.white, margin: '0 0 8px' },
  text: { fontSize: '13px', color: colors.muted, margin: '0 0 16px' },
  urlRow: { display: 'flex', gap: '8px', marginBottom: '12px' },
  urlInput: {
    flex: 1, padding: '8px 12px', borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`, background: colors.ink,
    color: colors.white, fontSize: '12px', fontFamily: font.family,
  },
  copyBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: 'none',
    background: colors.cyan, color: colors.ink, fontWeight: 600, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  expiry: { fontSize: '12px', color: colors.muted, margin: '0 0 16px' },
  revokeBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: `1px solid ${colors.red}40`,
    background: 'transparent', color: colors.red, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
}
