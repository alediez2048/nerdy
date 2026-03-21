// PD-09: Standalone Competitive Intel page
import { useEffect, useState } from 'react'
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

const ARROW: Record<string, string> = { rising: '\u2191', falling: '\u2193', stable: '\u2192' }
const ARROW_COLOR: Record<string, string> = { rising: colors.mint, falling: colors.red, stable: colors.muted }

export default function CompetitiveIntelPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadCompetitor, setUploadCompetitor] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<Record<string, unknown> | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const reload = () => {
    fetchCompetitive().then(setData).catch((e) => setError(e.message))
  }

  useEffect(() => {
    reload()
  }, [])

  const handleUpload = async () => {
    if (!uploadFile || !uploadCompetitor.trim()) return
    setUploading(true)
    setUploadError(null)
    setUploadResult(null)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('competitor_name', uploadCompetitor.trim())
      const token = localStorage.getItem('token')
      const headers: HeadersInit = {}
      if (token) headers['Authorization'] = `Bearer ${token}`
      const res = await fetch('/api/competitive/upload', { method: 'POST', headers, body: formData })
      if (!res.ok) throw new Error(await res.text())
      const result = await res.json()
      if (result.error) { setUploadError(result.error); return }
      setUploadResult(result)
      setUploadFile(null)
      setUploadCompetitor('')
      reload()
    } catch (e: unknown) {
      setUploadError(e instanceof Error ? e.message : String(e))
    } finally {
      setUploading(false)
    }
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
      {/* Upload section */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ ...s.pageTitle, marginBottom: 0 }}>Competitive Intelligence</h1>
        <button onClick={() => setShowUpload(!showUpload)}
          style={{ padding: '8px 16px', borderRadius: radii.button, border: `1px solid ${colors.cyan}40`,
            background: 'transparent', color: colors.cyan, cursor: 'pointer', fontSize: '13px', fontFamily: font.family }}>
          {showUpload ? 'Close Upload' : 'Upload Competitor Data'}
        </button>
      </div>
      {showUpload && (
        <div style={{ background: colors.surface, borderRadius: radii.card, padding: '20px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' as const }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ fontSize: '12px', color: colors.muted, display: 'block', marginBottom: '4px', fontFamily: font.family }}>Competitor Name</label>
              <input type="text" value={uploadCompetitor} onChange={(e) => setUploadCompetitor(e.target.value)}
                placeholder="e.g. Princeton Review" style={{ width: '100%', padding: '8px 12px', borderRadius: '8px',
                  border: `1px solid ${colors.muted}30`, background: colors.ink, color: colors.white,
                  fontSize: '14px', fontFamily: font.family, boxSizing: 'border-box' as const }} />
            </div>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ fontSize: '12px', color: colors.muted, display: 'block', marginBottom: '4px', fontFamily: font.family }}>JSON File (Meta Ad Library export)</label>
              <input type="file" accept=".json" onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                style={{ fontSize: '13px', color: colors.muted, fontFamily: font.family }} />
            </div>
            <button onClick={handleUpload} disabled={uploading || !uploadFile || !uploadCompetitor.trim()}
              style={{ padding: '8px 20px', borderRadius: radii.button, border: 'none',
                background: uploading || !uploadFile || !uploadCompetitor.trim() ? colors.muted + '40' : `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
                color: colors.ink, fontWeight: 600, fontSize: '13px', cursor: 'pointer', fontFamily: font.family }}>
              {uploading ? 'Uploading...' : 'Upload & Classify'}
            </button>
          </div>
          {uploadError && <p style={{ color: colors.red, fontSize: '13px', marginTop: '8px', fontFamily: font.family }}>{uploadError}</p>}
          {uploadResult && (
            <div style={{ marginTop: '12px', padding: '12px', background: colors.ink, borderRadius: '8px', fontSize: '13px', color: colors.mint, fontFamily: font.family }}>
              Added <strong>{uploadResult.ads_new as number}</strong> new ads ({uploadResult.ads_duplicate as number} duplicates skipped),{' '}
              <strong>{uploadResult.patterns_added as number}</strong> patterns classified for <strong>{uploadResult.competitor as string}</strong>
            </div>
          )}
        </div>
      )}
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

      {/* How competitive data flows into ad generation */}
      <div style={s.explainer}>
        <h3 style={s.explainerTitle}>How this data powers ad generation</h3>
        <div style={s.explainerSteps}>
          <div style={s.explainerStep}>
            <span style={s.stepNum}>1</span>
            <div>
              <strong style={{ color: colors.white }}>Scrape & Classify</strong>
              <p style={s.explainerText}>
                Competitor ads are scraped from Meta Ad Library and classified into structural patterns:
                hook type, body pattern, CTA style, and emotional register. This is the raw competitive intelligence.
              </p>
            </div>
          </div>
          <div style={s.explainerStep}>
            <span style={s.stepNum}>2</span>
            <div>
              <strong style={{ color: colors.white }}>Brief Expansion</strong>
              <p style={s.explainerText}>
                When a session runs, the brief expansion step calls <code style={s.code}>get_landscape_context()</code> to
                inject competitive insights into the prompt — what hooks competitors favor, what emotional angles they play,
                and how Varsity Tutors can differentiate.
              </p>
            </div>
          </div>
          <div style={s.explainerStep}>
            <span style={s.stepNum}>3</span>
            <div>
              <strong style={{ color: colors.white }}>Structural Atom Selection</strong>
              <p style={s.explainerText}>
                The ad generator calls <code style={s.code}>query_patterns()</code> to pull proven structural atoms from the
                competitive pattern database. Instead of inventing ad structures, it recombines hook types, body patterns,
                and CTA styles that work in the SAT prep market — fitted to the Varsity Tutors brand voice.
              </p>
            </div>
          </div>
          <div style={s.explainerStep}>
            <span style={s.stepNum}>4</span>
            <div>
              <strong style={{ color: colors.white }}>Gap Analysis</strong>
              <p style={s.explainerText}>
                Underutilized hook types and emotional registers represent differentiation opportunities.
                If competitors lean heavily on fear-based hooks, the system can explore aspirational or social-proof
                approaches that the market isn't saturating.
              </p>
            </div>
          </div>
        </div>
      </div>

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
  explainer: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '24px 28px',
    marginBottom: '32px',
    borderLeft: `3px solid ${colors.cyan}`,
  },
  explainerTitle: {
    fontSize: '16px',
    fontWeight: 700,
    color: colors.white,
    margin: '0 0 16px',
    fontFamily: font.family,
  },
  explainerSteps: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '16px',
  },
  explainerStep: {
    display: 'flex',
    gap: '14px',
    alignItems: 'flex-start',
  },
  stepNum: {
    width: '26px',
    height: '26px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    color: colors.ink,
    fontWeight: 700,
    fontSize: '13px',
    flexShrink: 0,
    marginTop: '2px',
    fontFamily: font.family,
  },
  explainerText: {
    fontSize: '13px',
    color: colors.muted,
    margin: '4px 0 0',
    lineHeight: 1.5,
    fontFamily: font.family,
  },
  code: {
    background: `${colors.muted}20`,
    padding: '1px 6px',
    borderRadius: '4px',
    fontSize: '12px',
    color: colors.cyan,
    fontFamily: 'monospace',
  },
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
}
