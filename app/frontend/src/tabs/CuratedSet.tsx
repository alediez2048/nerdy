// PA-10: Curated Set tab — select, reorder, annotate, edit, export
import { useEffect, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import {
  getCuratedSet,
  createCuratedSet,
  removeAdFromCurated,
  updateCuratedAd,
  batchReorder,
  downloadExportZip,
  type CuratedAd,
  type CuratedSetData,
} from '../api/curation'
import { fetchAds } from '../api/dashboard'
import Badge from '../components/Badge'

interface AdData {
  ad_id: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  image_url: string | null
}

export default function CuratedSet({ sessionId }: { sessionId: string }) {
  const [curatedSet, setCuratedSet] = useState<CuratedSetData | null>(null)
  const [adMap, setAdMap] = useState<Record<string, AdData>>({})
  const [loading, setLoading] = useState(true)
  const [editingAd, setEditingAd] = useState<CuratedAd | null>(null)
  const [editText, setEditText] = useState('')
  const [exporting, setExporting] = useState(false)

  const reload = async () => {
    setLoading(true)
    const data = await getCuratedSet(sessionId).catch(() => null)
    setCuratedSet(data)
    setLoading(false)
  }

  useEffect(() => {
    reload()
    fetchAds(sessionId)
      .then((data) => {
        const lib = (data.ad_library || []) as AdData[]
        const map: Record<string, AdData> = {}
        lib.forEach((a) => { map[a.ad_id] = a })
        setAdMap(map)
      })
      .catch(() => {})
  }, [sessionId])

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
    const ad = adMap[editingAd.ad_id]
    await updateCuratedAd(sessionId, editingAd.ad_id, {
      edited_copy: {
        primary_text: {
          original: ad?.copy?.primary_text || '',
          edited: editText,
        },
      },
    })
    setEditingAd(null)
    await reload()
  }

  if (loading) return <p style={{ color: colors.muted }}>Loading...</p>

  if (!curatedSet || curatedSet.ads.length === 0) {
    return (
      <div style={s.emptyWrap}>
        <div style={s.empty}>
          <h3 style={s.emptyTitle}>Curated Set</h3>
          <p style={s.emptyText}>
            Your curated set is a hand-picked collection of your best ads, ready for export
            and deployment. Here's the workflow:
          </p>
          <div style={s.steps}>
            <div style={s.step}><span style={s.stepNum}>1</span><span>Browse the <strong>Ad Library</strong> tab and expand any ad</span></div>
            <div style={s.step}><span style={s.stepNum}>2</span><span>Click <strong>Add to Curated Set</strong> on your best published ads</span></div>
            <div style={s.step}><span style={s.stepNum}>3</span><span>Return here to <strong>reorder, annotate, edit copy,</strong> and <strong>export</strong></span></div>
          </div>
          {!curatedSet && (
            <button onClick={handleCreate} style={s.createBtn}>Create Curated Set</button>
          )}
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div style={s.header}>
        <div>
          <span style={s.count}>{curatedSet.ads.length} ad{curatedSet.ads.length !== 1 ? 's' : ''} curated</span>
          <p style={s.headerDesc}>
            Reorder with arrows, add notes, edit copy. Export when ready.
          </p>
        </div>
        <div style={s.exportGroup}>
          <button
            onClick={async () => {
              setExporting(true)
              try { await downloadExportZip(sessionId) } catch (e) { alert(`Export failed: ${e}`) }
              setExporting(false)
            }}
            style={s.exportBtn}
            disabled={exporting}
          >
            {exporting ? 'Exporting...' : 'Export ZIP'}
          </button>
        </div>
      </div>

      {/* Export format info */}
      <div style={s.exportInfo}>
        <strong>Export includes:</strong> Per-ad folders with copy (JSON), images, metadata, annotations.
        Plus a manifest CSV and summary JSON — ready for Meta Ads Manager bulk import.
      </div>

      {/* Ad list */}
      <div style={s.list}>
        {curatedSet.ads.map((cad, i) => {
          const ad = adMap[cad.ad_id]
          return (
            <div key={cad.ad_id} style={s.card}>
              <div style={s.cardLayout}>
                {/* Image preview */}
                {ad?.image_url && (
                  <img
                    src={`/api${ad.image_url}`}
                    alt={cad.ad_id}
                    style={s.cardImage}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                )}
                <div style={s.cardBody}>
                  <div style={s.cardHeader}>
                    <div style={s.posRow}>
                      <span style={s.position}>{cad.position || i + 1}</span>
                      <span style={s.adId}>{cad.ad_id}</span>
                      {cad.edited_copy && <Badge label="Edited" color={colors.lightPurple} />}
                      {ad && <Badge label={ad.aggregate_score.toFixed(1)} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />}
                    </div>
                    <div style={s.actions}>
                      <button onClick={() => handleMoveUp(i)} style={s.arrowBtn} disabled={i === 0}>↑</button>
                      <button onClick={() => handleMoveDown(i)} style={s.arrowBtn} disabled={i === curatedSet.ads.length - 1}>↓</button>
                      <button onClick={() => { setEditingAd(cad); setEditText(ad?.copy?.primary_text || '') }} style={s.editBtn}>Edit Copy</button>
                      <button onClick={() => handleRemove(cad.ad_id)} style={s.removeBtn}>Remove</button>
                    </div>
                  </div>

                  {/* Ad copy preview */}
                  <p style={s.copyPreview}>
                    {ad?.copy?.primary_text || '—'}
                  </p>
                  {ad?.copy?.headline && (
                    <p style={s.headline}><strong>Headline:</strong> {ad.copy.headline}</p>
                  )}

                  {/* Annotation */}
                  <input
                    type="text"
                    placeholder="Add a note (e.g. 'For Q2 campaign', 'Needs legal review')..."
                    defaultValue={cad.annotation || ''}
                    onBlur={(e) => {
                      if (e.target.value !== (cad.annotation || '')) {
                        handleAnnotate(cad.ad_id, e.target.value)
                      }
                    }}
                    onClick={(e) => e.stopPropagation()}
                    style={s.annotationInput}
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Edit modal */}
      {editingAd && (
        <div style={s.modal} onClick={() => setEditingAd(null)}>
          <div style={s.modalContent} onClick={(e) => e.stopPropagation()}>
            <h3 style={s.modalTitle}>Edit Ad Copy</h3>
            <p style={s.modalSub}>{editingAd.ad_id}</p>
            <p style={s.modalHint}>
              Edit the primary text below. The original is preserved — exports include both
              original and edited versions for comparison.
            </p>
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              placeholder="Enter edited copy..."
              style={s.textarea}
              rows={6}
            />
            <div style={s.modalActions}>
              <button onClick={() => setEditingAd(null)} style={s.discardBtn}>Cancel</button>
              <button onClick={handleSaveEdit} style={s.saveBtn}>Save Edit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  emptyWrap: { display: 'flex', justifyContent: 'center', padding: '20px 0' },
  empty: { textAlign: 'center', padding: '48px 32px', background: colors.surface, borderRadius: radii.card, maxWidth: '560px' },
  emptyTitle: { fontSize: '20px', fontWeight: 700, color: colors.white, margin: '0 0 8px', fontFamily: font.family },
  emptyText: { fontSize: '14px', color: colors.muted, margin: '0 0 20px', lineHeight: 1.5, fontFamily: font.family },
  steps: { display: 'flex', flexDirection: 'column' as const, gap: '12px', textAlign: 'left' as const, marginBottom: '24px' },
  step: { display: 'flex', alignItems: 'center', gap: '12px', fontSize: '14px', color: colors.white, fontFamily: font.family },
  stepNum: {
    width: '28px', height: '28px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`, color: colors.ink,
    fontWeight: 700, fontSize: '13px', flexShrink: 0,
  },
  createBtn: {
    padding: '10px 24px', borderRadius: radii.button, border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink, fontWeight: 700, fontSize: '14px', cursor: 'pointer', fontFamily: font.family,
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' },
  count: { fontSize: '16px', fontWeight: 600, color: colors.white, fontFamily: font.family },
  headerDesc: { fontSize: '13px', color: colors.muted, margin: '4px 0 0', fontFamily: font.family },
  exportGroup: { display: 'flex', gap: '8px' },
  exportBtn: {
    padding: '8px 20px', borderRadius: radii.button, border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink, fontWeight: 600, fontSize: '13px',
    cursor: 'pointer', fontFamily: font.family, textDecoration: 'none',
  },
  exportInfo: {
    fontSize: '12px', color: colors.muted, background: colors.surface, borderRadius: radii.input,
    padding: '10px 14px', marginBottom: '16px', lineHeight: 1.5, fontFamily: font.family,
  },
  list: { display: 'flex', flexDirection: 'column' as const, gap: '10px' },
  card: { background: colors.surface, borderRadius: radii.card, overflow: 'hidden', fontFamily: font.family },
  cardLayout: { display: 'flex' },
  cardImage: {
    width: '140px', minWidth: '140px', objectFit: 'cover' as const, display: 'block',
    borderRight: `1px solid ${colors.muted}15`,
  },
  cardBody: { flex: 1, padding: '12px 16px' },
  cardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  posRow: { display: 'flex', alignItems: 'center', gap: '8px' },
  position: { fontSize: '20px', fontWeight: 700, color: colors.cyan, width: '28px' },
  adId: { fontSize: '11px', color: colors.muted },
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
    padding: '4px 12px', borderRadius: radii.button, border: `1px solid ${colors.red}40`,
    background: 'transparent', color: colors.red, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  copyPreview: { fontSize: '13px', color: colors.white, margin: '0 0 4px', lineHeight: 1.4 },
  headline: { fontSize: '12px', color: colors.muted, margin: '0 0 8px' },
  annotationInput: {
    width: '100%', padding: '6px 10px', borderRadius: '8px',
    border: `1px solid ${colors.muted}20`, background: colors.ink,
    color: colors.white, fontSize: '12px', fontFamily: font.family, boxSizing: 'border-box' as const,
  },
  modal: {
    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
    background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center', alignItems: 'center',
    zIndex: 1000,
  },
  modalContent: {
    background: colors.surface, borderRadius: radii.card, padding: '32px',
    width: '100%', maxWidth: '540px', fontFamily: font.family,
  },
  modalTitle: { fontSize: '18px', fontWeight: 600, color: colors.white, margin: '0 0 4px' },
  modalSub: { fontSize: '12px', color: colors.muted, margin: '0 0 12px' },
  modalHint: { fontSize: '13px', color: colors.muted, margin: '0 0 12px', lineHeight: 1.5 },
  textarea: {
    width: '100%', padding: '10px', borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`, background: colors.ink,
    color: colors.white, fontSize: '14px', fontFamily: font.family,
    resize: 'vertical' as const, boxSizing: 'border-box' as const,
  },
  modalActions: { display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '16px' },
  discardBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontFamily: font.family,
  },
  saveBtn: {
    padding: '8px 16px', borderRadius: radii.button, border: 'none',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink, fontWeight: 600, cursor: 'pointer', fontFamily: font.family,
  },
}
