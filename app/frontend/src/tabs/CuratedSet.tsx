// PA-10: Curated Set tab — select, reorder, annotate, edit, export
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import {
  getCuratedSet,
  createCuratedSet,
  removeAdFromCurated,
  updateCuratedAd,
  batchReorder,
  getExportUrl,
  type CuratedAd,
  type CuratedSetData,
} from '../api/curation'
import Badge from '../components/Badge'

export default function CuratedSet({ sessionId }: { sessionId: string }) {
  const [curatedSet, setCuratedSet] = useState<CuratedSetData | null>(null)
  const [loading, setLoading] = useState(true)
  const [editingAd, setEditingAd] = useState<CuratedAd | null>(null)
  const [editText, setEditText] = useState('')

  const reload = async () => {
    setLoading(true)
    const data = await getCuratedSet(sessionId).catch(() => null)
    setCuratedSet(data)
    setLoading(false)
  }

  useEffect(() => { reload() }, [sessionId])

  const handleCreate = async () => {
    await createCuratedSet(sessionId)
    await reload()
  }

  const handleRemove = async (adId: string) => {
    await removeAdFromCurated(sessionId, adId)
    await reload()
  }

  const handleAnnotate = async (adId: string, annotation: string) => {
    await updateCuratedAd(sessionId, adId, { annotation })
    await reload()
  }

  const handleMoveUp = async (index: number) => {
    if (!curatedSet || index <= 0) return
    const ids = curatedSet.ads.map((a) => a.ad_id)
    ;[ids[index - 1], ids[index]] = [ids[index], ids[index - 1]]
    await batchReorder(sessionId, ids)
    await reload()
  }

  const handleMoveDown = async (index: number) => {
    if (!curatedSet || index >= curatedSet.ads.length - 1) return
    const ids = curatedSet.ads.map((a) => a.ad_id)
    ;[ids[index], ids[index + 1]] = [ids[index + 1], ids[index]]
    await batchReorder(sessionId, ids)
    await reload()
  }

  const handleSaveEdit = async () => {
    if (!editingAd) return
    await updateCuratedAd(sessionId, editingAd.ad_id, {
      edited_copy: {
        primary_text: {
          original: (editingAd.edited_copy?.primary_text as Record<string, string>)?.original || '',
          edited: editText,
        },
      },
    })
    setEditingAd(null)
    await reload()
  }

  if (loading) return <p style={{ color: colors.muted }}>Loading...</p>

  // Empty state
  if (!curatedSet || curatedSet.ads.length === 0) {
    return (
      <div style={s.empty}>
        <h3 style={s.emptyTitle}>No curated ads yet</h3>
        <p style={s.emptyText}>
          Browse the Ad Library tab, then add your best ads here for review and export.
        </p>
        {!curatedSet && (
          <button onClick={handleCreate} style={s.createBtn}>Create Curated Set</button>
        )}
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={s.header}>
        <span style={s.count}>{curatedSet.ads.length} ads curated</span>
        <a href={getExportUrl(sessionId)} style={s.exportBtn} download>
          Export Meta-Ready ZIP
        </a>
      </div>

      {/* Ad list */}
      <div style={s.list}>
        {curatedSet.ads.map((ad, i) => (
          <div key={ad.ad_id} style={s.card}>
            <div style={s.cardHeader}>
              <div style={s.posRow}>
                <span style={s.position}>{ad.position}</span>
                <span style={s.adId}>{ad.ad_id}</span>
                {ad.edited_copy && <Badge label="Edited" color={colors.lightPurple} />}
              </div>
              <div style={s.actions}>
                <button onClick={() => handleMoveUp(i)} style={s.arrowBtn} disabled={i === 0}>↑</button>
                <button onClick={() => handleMoveDown(i)} style={s.arrowBtn} disabled={i === curatedSet.ads.length - 1}>↓</button>
                <button onClick={() => { setEditingAd(ad); setEditText('') }} style={s.editBtn}>Edit</button>
                <button onClick={() => handleRemove(ad.ad_id)} style={s.removeBtn}>×</button>
              </div>
            </div>

            {/* Annotation */}
            <input
              type="text"
              placeholder="Add a note..."
              defaultValue={ad.annotation || ''}
              onBlur={(e) => {
                if (e.target.value !== (ad.annotation || '')) {
                  handleAnnotate(ad.ad_id, e.target.value)
                }
              }}
              style={s.annotationInput}
            />
          </div>
        ))}
      </div>

      {/* Edit modal */}
      {editingAd && (
        <div style={s.modal}>
          <div style={s.modalContent}>
            <h3 style={s.modalTitle}>Edit Ad Copy — {editingAd.ad_id}</h3>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              placeholder="Enter edited copy..."
              style={s.textarea}
              rows={5}
            />
            <div style={s.modalActions}>
              <button onClick={() => setEditingAd(null)} style={s.discardBtn}>Discard</button>
              <button onClick={handleSaveEdit} style={s.saveBtn}>Save Edit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  empty: { textAlign: 'center', padding: '60px 20px', background: colors.surface, borderRadius: radii.card },
  emptyTitle: { fontSize: '18px', fontWeight: 600, color: colors.white, margin: '0 0 8px', fontFamily: font.family },
  emptyText: { fontSize: '14px', color: colors.muted, margin: '0 0 16px', fontFamily: font.family },
  createBtn: {
    padding: '10px 24px', borderRadius: radii.button, border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink, fontWeight: 700, fontSize: '14px', cursor: 'pointer', fontFamily: font.family,
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' },
  count: { fontSize: '14px', color: colors.muted, fontFamily: font.family },
  exportBtn: {
    padding: '8px 20px', borderRadius: radii.button, border: 'none',
    background: colors.mint, color: colors.ink, fontWeight: 600, fontSize: '13px',
    cursor: 'pointer', fontFamily: font.family, textDecoration: 'none',
  },
  list: { display: 'flex', flexDirection: 'column', gap: '8px' },
  card: { background: colors.surface, borderRadius: radii.input, padding: '14px 18px', fontFamily: font.family },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  posRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  position: { fontSize: '18px', fontWeight: 700, color: colors.cyan, width: '28px' },
  adId: { fontSize: '12px', color: colors.muted },
  actions: { display: 'flex', gap: '6px' },
  arrowBtn: {
    padding: '4px 8px', borderRadius: '6px', border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontSize: '14px',
  },
  editBtn: {
    padding: '4px 12px', borderRadius: radii.button, border: `1px solid ${colors.cyan}40`,
    background: 'transparent', color: colors.cyan, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  removeBtn: {
    padding: '4px 8px', borderRadius: '6px', border: `1px solid ${colors.red}40`,
    background: 'transparent', color: colors.red, cursor: 'pointer', fontSize: '16px',
  },
  annotationInput: {
    width: '100%', padding: '6px 10px', borderRadius: '8px',
    border: `1px solid ${colors.muted}20`, background: colors.ink,
    color: colors.white, fontSize: '12px', fontFamily: font.family, boxSizing: 'border-box',
  },
  modal: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: colors.surface, borderRadius: radii.card, padding: '32px',
    width: '100%', maxWidth: '500px', fontFamily: font.family,
  },
  modalTitle: { fontSize: '18px', fontWeight: 600, color: colors.white, margin: '0 0 16px' },
  textarea: {
    width: '100%', padding: '10px', borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`, background: colors.ink,
    color: colors.white, fontSize: '14px', fontFamily: font.family,
    resize: 'vertical', boxSizing: 'border-box',
  },
  modalActions: { display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' },
  discardBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontFamily: font.family,
  },
  saveBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: 'none',
    background: colors.cyan, color: colors.ink, fontWeight: 600, cursor: 'pointer', fontFamily: font.family,
  },
}
