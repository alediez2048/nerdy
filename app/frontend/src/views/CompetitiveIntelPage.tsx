// PD-09 + PD-11: Standalone Competitive Intel page with upload
import { useCallback, useEffect, useRef, useState } from 'react'
import { colors, radii, font } from '../design/tokens'
import { fetchCompetitive } from '../api/dashboard'

interface CompSummary {
  strategy: string
  dominant_hooks: string[]
  emotional_levers: string[]
  gaps: string
}

interface GapItem {
  hook_type: string
  coverage_pct: number
  opportunity: string
}

interface Metadata {
  total_ads_scraped?: number
  unique_ads?: number
  pattern_records?: number
  source?: string
  competitors?: string[]
}

interface TrendItem {
  hook_type: string
  direction: 'rising' | 'falling' | 'stable'
  description?: string
}

interface UploadResult {
  ads_parsed: number
  ads_new: number
  ads_duplicate: number
  patterns_added: number
  competitor: string
  error?: string
}

const ARROW: Record<string, string> = { rising: '\u2191', falling: '\u2193', stable: '\u2192' }
const ARROW_COLOR: Record<string, string> = { rising: colors.mint, falling: colors.red, stable: colors.muted }

export default function CompetitiveIntelPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Upload state (PD-11)
  const [uploadExpanded, setUploadExpanded] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadCompetitor, setUploadCompetitor] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const reload = useCallback(() => {
    fetchCompetitive().then(setData).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  const handleUpload = async () => {
    if (!uploadFile || !uploadCompetitor.trim()) return
    setUploading(true)
    setUploadResult(null)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('competitor_name', uploadCompetitor.trim())

      const token = localStorage.getItem('token')
      const headers: HeadersInit = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch('/api/competitive/upload', {
        method: 'POST',
        headers,
        body: formData,
      })
      if (!res.ok) throw new Error(await res.text())
      const result: UploadResult = await res.json()
      setUploadResult(result)
      setUploadFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      reload()
    } catch (e) {
      setUploadResult({ ads_parsed: 0, ads_new: 0, ads_duplicate: 0, patterns_added: 0, competitor: '', error: String(e) })
    }
    setUploading(false)
  }

  if (error)
    return (
      <div style={s.page}>
        <p style={{ color: colors.red, fontFamily: font.family }}>{error}</p>
      </div>
    )
  if (!data)
    return (
      <div style={s.page}>
        <p style={{ color: colors.muted, fontFamily: font.family }}>Loading competitive intelligence...</p>
      </div>
    )
  if (Object.keys(data).length === 0)
    return (
      <div style={s.page}>
        <p style={{ color: colors.muted, fontFamily: font.family }}>No competitive data available</p>
      </div>
    )

  const hookDist = (data.hook_distribution || data.hook_type_counts || data.hook_types || {}) as Record<string, number>
  const gapAnalysis = (data.gap_analysis || []) as GapItem[]
  const summaries = (data.competitor_summaries || {}) as Record<string, CompSummary>
  const metadata = (data.metadata || {}) as Metadata
  const trends = (data.temporal_trends || []) as TrendItem[]

  return (
    <div style={s.page}>
      {/* Page title + metadata bar */}
      <h1 style={s.pageTitle}>Competitive Intelligence</h1>
      <div style={s.metaBar}>
        <span style={s.metaItem}>{metadata.total_ads_scraped || '200+'} ads scraped</span>
        <span style={s.metaDot}>&middot;</span>
        <span style={s.metaItem}>{metadata.unique_ads || 0} unique ads</span>
        <span style={s.metaDot}>&middot;</span>
        <span style={s.metaItem}>{metadata.competitors?.length || 4} competitors</span>
        {metadata.source && (
          <>
            <span style={s.metaDot}>&middot;</span>
            <span style={s.metaItem}>Source: {metadata.source}</span>
          </>
        )}
      </div>

      {/* PD-11: Upload Competitor Data */}
      <section style={s.section}>
        <button
          onClick={() => setUploadExpanded((v) => !v)}
          style={s.uploadToggle}
        >
          {uploadExpanded ? '- Hide' : '+ Upload Competitor Data'}
        </button>

        {uploadExpanded && (
          <div style={s.uploadPanel}>
            <div style={s.uploadRow}>
              <label style={s.uploadLabel}>
                Competitor Name
                <input
                  type="text"
                  value={uploadCompetitor}
                  onChange={(e) => setUploadCompetitor(e.target.value)}
                  placeholder="e.g. Princeton Review"
                  style={s.uploadInput}
                />
              </label>
              <label style={s.uploadLabel}>
                JSON File (Meta Ad Library export)
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".json"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  style={s.uploadFileInput}
                />
              </label>
            </div>
            <button
              onClick={handleUpload}
              disabled={uploading || !uploadFile || !uploadCompetitor.trim()}
              style={{
                ...s.uploadBtn,
                opacity: uploading || !uploadFile || !uploadCompetitor.trim() ? 0.5 : 1,
              }}
            >
              {uploading ? 'Uploading...' : 'Upload & Classify'}
            </button>

            {uploadResult && !uploadResult.error && (
              <div style={s.uploadSuccess}>
                Processed {uploadResult.ads_parsed} ads for <strong>{uploadResult.competitor}</strong>
                {' '}&mdash; {uploadResult.ads_new} new, {uploadResult.ads_duplicate} duplicates, {uploadResult.patterns_added} patterns added.
              </div>
            )}
            {uploadResult?.error && (
              <div style={s.uploadError}>{uploadResult.error}</div>
            )}
          </div>
        )}
      </section>

      {/* Section 1 — Competitor Profiles */}
      {Object.keys(summaries).length > 0 && (
        <section style={s.section}>
          <h2 style={s.sectionTitle}>Competitor Profiles</h2>
          <div style={s.compGrid}>
            {Object.entries(summaries).map(([name, info]) => (
              <div key={name} style={s.card}>
                <h3 style={s.compName}>{name}</h3>
                <p style={s.compStrategy}>{info.strategy}</p>

                {/* Dominant hooks */}
                {info.dominant_hooks?.length > 0 && (
                  <div style={s.tagRow}>
                    {info.dominant_hooks.map((h) => (
                      <span key={h} style={s.hookBadge}>{h.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                )}

                {/* Emotional levers */}
                {info.emotional_levers?.length > 0 && (
                  <div style={s.tagRow}>
                    {info.emotional_levers.map((e) => (
                      <span key={e} style={s.emotionBadge}>{e.replace(/_/g, ' ')}</span>
                    ))}
                  </div>
                )}

                {/* Gaps */}
                {info.gaps && (
                  <div style={s.gapNote}>
                    <strong>Gaps:</strong> {info.gaps}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Section 2 — Landscape Analytics */}
      <section style={s.section}>
        <h2 style={s.sectionTitle}>Landscape Analytics</h2>

        {/* Hook distribution bar chart */}
        <div style={s.subsection}>
          <h3 style={s.subheading}>Hook Distribution</h3>
          <HookBarChart data={hookDist} />
        </div>

        {/* Gap analysis list */}
        {gapAnalysis.length > 0 && (
          <div style={s.subsection}>
            <h3 style={s.subheading}>Gap Analysis</h3>
            <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '8px' }}>
              {gapAnalysis.map((g) => (
                <div key={g.hook_type} style={s.gapRow}>
                  <span style={s.gapHook}>{g.hook_type.replace(/_/g, ' ')}</span>
                  <span style={s.gapPct}>{g.coverage_pct.toFixed(0)}%</span>
                  <span style={s.gapOpp}>{g.opportunity}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Temporal trends */}
        {trends.length > 0 && (
          <div style={s.subsection}>
            <h3 style={s.subheading}>Temporal Trends</h3>
            <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '6px' }}>
              {trends.map((t) => (
                <div key={t.hook_type} style={s.trendRow}>
                  <span style={{ ...s.trendArrow, color: ARROW_COLOR[t.direction] || colors.muted }}>
                    {ARROW[t.direction] || '-'}
                  </span>
                  <span style={s.trendLabel}>{t.hook_type.replace(/_/g, ' ')}</span>
                  <span style={s.trendDir}>{t.direction}</span>
                  {t.description && <span style={s.trendDesc}>{t.description}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  )
}

/* ---- Hook Distribution horizontal bar chart ---- */
function HookBarChart({ data }: { data: Record<string, number> }) {
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a)
  const max = sorted[0]?.[1] || 1

  if (sorted.length === 0)
    return <p style={{ color: colors.muted, fontSize: '13px', fontFamily: font.family }}>No data</p>

  return (
    <div>
      {sorted.map(([label, count]) => (
        <div key={label} style={s.barRow}>
          <span style={s.barLabel}>{label.replace(/_/g, ' ')}</span>
          <div style={s.barTrack}>
            <div
              style={{
                width: `${(count / max) * 100}%`,
                height: '100%',
                background: colors.cyan,
                borderRadius: '4px',
              }}
            />
          </div>
          <span style={s.barValue}>
            {typeof count === 'number' && count < 1 ? `${(count * 100).toFixed(0)}%` : count}
          </span>
        </div>
      ))}
    </div>
  )
}

/* ---- Styles ---- */
const s: Record<string, React.CSSProperties> = {
  page: {
    background: colors.ink,
    minHeight: '100vh',
    padding: '96px 48px 64px',
    fontFamily: font.family,
  },
  pageTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: colors.white,
    margin: '0 0 8px',
    fontFamily: font.family,
  },
  metaBar: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '40px',
  },
  metaItem: {
    fontSize: '13px',
    color: colors.muted,
    fontFamily: font.family,
  },
  metaDot: {
    fontSize: '13px',
    color: colors.muted,
  },

  /* Sections */
  section: {
    marginBottom: '48px',
  },
  sectionTitle: {
    fontSize: '20px',
    fontWeight: 600,
    color: colors.white,
    margin: '0 0 20px',
    fontFamily: font.family,
  },
  subsection: {
    marginBottom: '32px',
  },
  subheading: {
    fontSize: '15px',
    fontWeight: 600,
    color: colors.cyan,
    margin: '0 0 12px',
    fontFamily: font.family,
  },

  /* Competitor cards */
  compGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
    gap: '16px',
  },
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px',
    fontFamily: font.family,
  },
  compName: {
    fontSize: '16px',
    fontWeight: 700,
    color: colors.white,
    margin: '0 0 10px',
    fontFamily: font.family,
  },
  compStrategy: {
    fontSize: '13px',
    color: colors.muted,
    lineHeight: 1.6,
    margin: '0 0 14px',
    fontFamily: font.family,
  },
  tagRow: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap' as const,
    marginBottom: '10px',
  },
  hookBadge: {
    fontSize: '11px',
    padding: '3px 10px',
    borderRadius: '100px',
    background: `${colors.cyan}20`,
    color: colors.cyan,
    fontFamily: font.family,
  },
  emotionBadge: {
    fontSize: '11px',
    padding: '3px 10px',
    borderRadius: '100px',
    background: `${colors.lightPurple}20`,
    color: colors.lightPurple,
    fontFamily: font.family,
  },
  gapNote: {
    fontSize: '12px',
    color: colors.yellow,
    lineHeight: 1.4,
    borderTop: `1px solid ${colors.muted}20`,
    paddingTop: '10px',
    marginTop: '6px',
    fontFamily: font.family,
  },

  /* Bar chart */
  barRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '6px',
  },
  barLabel: {
    width: '140px',
    fontSize: '12px',
    color: colors.muted,
    textAlign: 'right' as const,
    fontFamily: font.family,
  },
  barTrack: {
    flex: 1,
    height: '18px',
    background: `${colors.muted}20`,
    borderRadius: '4px',
    overflow: 'hidden',
  },
  barValue: {
    fontSize: '12px',
    color: colors.white,
    width: '36px',
    fontFamily: font.family,
  },

  /* Gap analysis rows */
  gapRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    background: colors.surface,
    borderRadius: radii.input,
    padding: '12px 16px',
    fontFamily: font.family,
  },
  gapHook: {
    fontSize: '13px',
    color: colors.white,
    fontWeight: 600,
    minWidth: '120px',
  },
  gapPct: {
    fontSize: '13px',
    color: colors.yellow,
    fontWeight: 600,
    minWidth: '40px',
  },
  gapOpp: {
    fontSize: '12px',
    color: colors.muted,
    flex: 1,
  },

  /* Trend rows */
  trendRow: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
    background: colors.surface,
    borderRadius: radii.input,
    padding: '10px 16px',
    fontFamily: font.family,
  },
  trendArrow: {
    fontSize: '18px',
    fontWeight: 700,
    minWidth: '20px',
    textAlign: 'center' as const,
  },
  trendLabel: {
    fontSize: '13px',
    color: colors.white,
    fontWeight: 600,
    minWidth: '120px',
  },
  trendDir: {
    fontSize: '12px',
    color: colors.muted,
    minWidth: '60px',
    textTransform: 'capitalize' as const,
  },
  trendDesc: {
    fontSize: '12px',
    color: colors.muted,
    flex: 1,
  },

  /* Upload section (PD-11) */
  uploadToggle: {
    background: 'none',
    border: `1px solid ${colors.cyan}40`,
    borderRadius: radii.card,
    color: colors.cyan,
    fontSize: '14px',
    fontWeight: 600,
    fontFamily: font.family,
    padding: '10px 20px',
    cursor: 'pointer',
  },
  uploadPanel: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px',
    marginTop: '16px',
  },
  uploadRow: {
    display: 'flex',
    gap: '20px',
    flexWrap: 'wrap' as const,
    marginBottom: '16px',
  },
  uploadLabel: {
    fontSize: '13px',
    color: colors.muted,
    fontFamily: font.family,
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '6px',
    flex: 1,
    minWidth: '200px',
  },
  uploadInput: {
    background: colors.ink,
    border: `1px solid ${colors.muted}40`,
    borderRadius: radii.input,
    color: colors.white,
    padding: '8px 12px',
    fontSize: '14px',
    fontFamily: font.family,
    outline: 'none',
  },
  uploadFileInput: {
    background: colors.ink,
    border: `1px solid ${colors.muted}40`,
    borderRadius: radii.input,
    color: colors.muted,
    padding: '8px 12px',
    fontSize: '13px',
    fontFamily: font.family,
  },
  uploadBtn: {
    background: colors.cyan,
    border: 'none',
    borderRadius: radii.input,
    color: colors.ink,
    fontSize: '14px',
    fontWeight: 600,
    fontFamily: font.family,
    padding: '10px 24px',
    cursor: 'pointer',
  },
  uploadSuccess: {
    marginTop: '14px',
    fontSize: '13px',
    color: colors.mint,
    fontFamily: font.family,
    lineHeight: 1.5,
  },
  uploadError: {
    marginTop: '14px',
    fontSize: '13px',
    color: colors.red,
    fontFamily: font.family,
    lineHeight: 1.5,
  },
}
