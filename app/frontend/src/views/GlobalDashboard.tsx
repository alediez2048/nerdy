// Global Performance Dashboard — all-session pipeline data (8 tabs)
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import { fetchGlobalDashboard } from '../api/dashboard'
import Badge, { StatusBadge } from '../components/Badge'

// ── Types ──────────────────────────────────────────────────────────

interface PipelineSummary {
  total_ads_generated: number
  total_ads_published: number
  total_ads_discarded: number
  publish_rate: number
  total_batches: number
  total_tokens: number
  total_cost_usd: number
  avg_score: number
}

interface IterationCycle {
  ad_id: string
  cycle: number
  score_before: number
  score_after: number
  weakest_dimension: string
  action_taken: string
}

interface BatchScore {
  batch: number
  avg_score: number
  threshold: number
  published: number
  generated: number
  publish_rate: number
  tokens: number
}

interface Ad {
  ad_id: string
  brief_id: string
  copy: Record<string, string>
  scores: Record<string, number>
  aggregate_score: number
  rationale: Record<string, string>
  status: string
  cycle_count: number
  image_path: string | null
  image_url: string | null
}

// ── Tabs ───────────────────────────────────────────────────────────

const TABS = [
  { key: 'summary', label: 'Pipeline Summary' },
  { key: 'iterations', label: 'Iteration Cycles' },
  { key: 'quality', label: 'Quality Trends' },
  { key: 'dimensions', label: 'Dimension Deep-Dive' },
  { key: 'ads', label: 'Ad Library' },
  { key: 'costs', label: 'Token Economics' },
  { key: 'health', label: 'System Health' },
  { key: 'competitive', label: 'Competitive Intel' },
] as const

type TabKey = typeof TABS[number]['key']

// Theme is now handled globally via App.tsx ThemeToggle

// ── Main Component ─────────────────────────────────────────────────

export default function GlobalDashboard() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const activeTab = (searchParams.get('tab') as TabKey) || 'summary'

  useEffect(() => {
    fetchGlobalDashboard().then(setData).catch((e) => setError(e.message))
  }, [])

  const setTab = (tab: TabKey) => setSearchParams({ tab })

  if (error) {
    return (
      <div style={s.page}>
        <p style={{ color: colors.red }}>{error}</p>
        <a href="/sessions" style={{ color: colors.cyan }}>Back to Sessions</a>
      </div>
    )
  }

  if (!data) {
    return <div style={s.page}><p style={{ color: colors.muted }}>Loading global dashboard...</p></div>
  }

  return (
    <div style={s.page}>
      {/* Header */}
      <div style={s.header}>
        <div>
          <span onClick={() => navigate('/sessions')} style={s.backLink}>Sessions</span>
          <span style={{ color: colors.muted }}> / </span>
          <span style={{ color: colors.white }}>Global Dashboard</span>
        </div>
        <h1 style={s.title}>Performance Dashboard</h1>
        <p style={{ color: colors.muted, fontSize: '13px', margin: 0 }}>
          All pipeline data across every session
        </p>
      </div>

      {/* Tab bar */}
      <div style={s.tabBar}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setTab(tab.key)}
            style={activeTab === tab.key ? s.tabActive : s.tab}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={s.tabContent}>
        {activeTab === 'summary' && <PipelineSummaryTab data={data} />}
        {activeTab === 'iterations' && <IterationCyclesTab data={data} />}
        {activeTab === 'quality' && <QualityTrendsTab data={data} />}
        {activeTab === 'dimensions' && <DimensionDeepDiveTab data={data} />}
        {activeTab === 'ads' && <AdLibraryTab data={data} />}
        {activeTab === 'costs' && <TokenEconomicsTab data={data} />}
        {activeTab === 'health' && <SystemHealthTab data={data} />}
        {activeTab === 'competitive' && <CompetitiveIntelTab data={data} />}
      </div>
    </div>
  )
}

// ── Tab 1: Pipeline Summary ────────────────────────────────────────

function PipelineSummaryTab({ data }: { data: Record<string, unknown> }) {
  const ps = (data.pipeline_summary || {}) as PipelineSummary

  const metrics = [
    { label: 'Ads Generated', value: ps.total_ads_generated ?? 0, color: colors.white },
    { label: 'Ads Published', value: ps.total_ads_published ?? 0, color: colors.mint },
    { label: 'Publish Rate', value: ps.publish_rate ? `${(ps.publish_rate * 100).toFixed(0)}%` : '0%', color: colors.cyan },
    { label: 'Avg Score', value: ps.avg_score?.toFixed(1) ?? '0.0', color: colors.yellow },
    { label: 'Total Batches', value: ps.total_batches ?? 0, color: colors.white },
    { label: 'Total Tokens', value: (ps.total_tokens ?? 0).toLocaleString(), color: colors.white },
    { label: 'Total Cost', value: `$${(ps.total_cost_usd ?? 0).toFixed(2)}`, color: colors.yellow },
    { label: 'Ads Discarded', value: ps.total_ads_discarded ?? 0, color: colors.red },
  ]

  return (
    <div style={s.kpiGrid}>
      {metrics.map((m) => (
        <div key={m.label} style={s.kpiCard}>
          <div style={{ fontSize: '28px', fontWeight: 700, color: m.color, fontFamily: font.family }}>
            {String(m.value)}
          </div>
          <div style={{ fontSize: '12px', color: colors.muted, marginTop: '6px', fontFamily: font.family }}>
            {m.label}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Tab 2: Iteration Cycles ────────────────────────────────────────

function IterationCyclesTab({ data }: { data: Record<string, unknown> }) {
  const cycles = (data.iteration_cycles || []) as IterationCycle[]

  if (cycles.length === 0) return <p style={{ color: colors.muted }}>No iteration data available</p>

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
      {cycles.map((c) => {
        const delta = c.score_after - c.score_before
        const improved = delta > 0
        return (
          <div key={c.ad_id} style={s.cycleCard}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: colors.muted, fontFamily: font.family }}>{c.ad_id}</span>
              <StatusBadge status={c.action_taken} />
            </div>
            <div style={{ display: 'flex', gap: '16px', alignItems: 'center', marginTop: '10px' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: colors.muted }}>Before</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: colors.white, fontFamily: font.family }}>
                  {c.score_before.toFixed(1)}
                </div>
              </div>
              <div style={{ fontSize: '18px', color: improved ? colors.mint : colors.red, fontFamily: font.family }}>
                {improved ? '+' : ''}{delta.toFixed(1)}
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '11px', color: colors.muted }}>After</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: colors.white, fontFamily: font.family }}>
                  {c.score_after.toFixed(1)}
                </div>
              </div>
              <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
                <div style={{ fontSize: '11px', color: colors.muted }}>Weakest</div>
                <div style={{ fontSize: '13px', color: colors.yellow, fontFamily: font.family }}>
                  {c.weakest_dimension.replace(/_/g, ' ')}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Tab 3: Quality Trends ──────────────────────────────────────────

function QualityTrendsTab({ data }: { data: Record<string, unknown> }) {
  const trends = (data.quality_trends || {}) as Record<string, unknown>
  const batchScores = (trends.batch_scores || []) as BatchScore[]
  const distribution = (trends.score_distribution || []) as number[]

  return (
    <div>
      {/* Batch scores table */}
      <div style={s.section}>
        <h3 style={s.heading}>Batch Scores</h3>
        {batchScores.length === 0 ? (
          <p style={{ color: colors.muted }}>No batch data yet</p>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                {['Batch', 'Avg Score', 'Threshold', 'Published', 'Generated', 'Pub Rate', 'Tokens'].map((h) => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {batchScores.map((b) => (
                <tr key={b.batch}>
                  <td style={s.td}>{b.batch}</td>
                  <td style={{ ...s.td, color: b.avg_score >= 7 ? colors.mint : b.avg_score >= 5 ? colors.yellow : colors.red, fontWeight: 600 }}>
                    {b.avg_score.toFixed(1)}
                  </td>
                  <td style={s.td}>{b.threshold.toFixed(1)}</td>
                  <td style={{ ...s.td, color: colors.mint }}>{b.published}</td>
                  <td style={s.td}>{b.generated}</td>
                  <td style={s.td}>{(b.publish_rate * 100).toFixed(0)}%</td>
                  <td style={s.td}>{b.tokens.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Score distribution */}
      <div style={s.section}>
        <h3 style={s.heading}>Score Distribution</h3>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '120px' }}>
          {distribution.map((count, i) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', textAlign: 'center' }}>
              <div
                style={{
                  height: `${Math.min(count * 8, 100)}px`,
                  width: '100%',
                  background: i >= 7 ? colors.mint : i >= 5 ? colors.yellow : colors.red,
                  borderRadius: '4px 4px 0 0',
                }}
              />
              <div style={{ fontSize: '10px', color: colors.muted, marginTop: '2px' }}>{i}-{i + 1}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Tab 4: Dimension Deep-Dive ─────────────────────────────────────

function DimensionDeepDiveTab({ data }: { data: Record<string, unknown> }) {
  const dd = (data.dimension_deep_dive || {}) as Record<string, unknown>
  const dimTrends = (dd.dimension_trends || {}) as Record<string, number[]>
  const corrMatrix = (dd.correlation_matrix || {}) as Record<string, Record<string, number>>

  const dimensions = Object.keys(dimTrends)

  // Compute averages
  const dimAvgs: Record<string, { avg: number; count: number }> = {}
  for (const [dim, vals] of Object.entries(dimTrends)) {
    const arr = vals as number[]
    dimAvgs[dim] = {
      avg: arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0,
      count: arr.length,
    }
  }

  const corrColor = (r: number) => {
    const abs = Math.abs(r)
    if (abs >= 0.7) return `${colors.red}40`
    if (abs >= 0.3) return `${colors.yellow}40`
    return `${colors.mint}30`
  }

  return (
    <div>
      {/* Dimension averages */}
      <div style={s.section}>
        <h3 style={s.heading}>Dimension Averages</h3>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          {Object.entries(dimAvgs).map(([dim, { avg, count }]) => (
            <div key={dim} style={s.kpiCard}>
              <div style={{ fontSize: '22px', fontWeight: 700, color: avg >= 7 ? colors.mint : avg >= 5 ? colors.yellow : colors.red, fontFamily: font.family }}>
                {avg.toFixed(1)}
              </div>
              <div style={{ fontSize: '12px', color: colors.muted, marginTop: '4px', fontFamily: font.family }}>
                {dim.replace(/_/g, ' ')}
              </div>
              <div style={{ fontSize: '10px', color: colors.muted, fontFamily: font.family }}>
                n={count}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Correlation matrix */}
      {dimensions.length > 0 && Object.keys(corrMatrix).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Correlation Matrix</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={s.table}>
              <thead>
                <tr>
                  <th style={s.th}></th>
                  {dimensions.map((d) => (
                    <th key={d} style={{ ...s.th, fontSize: '10px' }}>{d.replace(/_/g, ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dimensions.map((d1) => (
                  <tr key={d1}>
                    <td style={{ ...s.td, fontSize: '11px', color: colors.muted, textAlign: 'right', paddingRight: '8px' }}>
                      {d1.replace(/_/g, ' ')}
                    </td>
                    {dimensions.map((d2) => {
                      const r = corrMatrix[d1]?.[d2]
                      return (
                        <td key={d2} style={{
                          ...s.td,
                          textAlign: 'center',
                          background: r != null ? corrColor(r) : 'transparent',
                          fontWeight: d1 === d2 ? 700 : 400,
                        }}>
                          {r != null ? r.toFixed(2) : '-'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: '16px', marginTop: '8px', fontSize: '11px', color: colors.muted }}>
            <span><span style={{ display: 'inline-block', width: '12px', height: '12px', background: `${colors.red}40`, borderRadius: '2px', marginRight: '4px', verticalAlign: 'middle' }} />r &gt; 0.7 (high)</span>
            <span><span style={{ display: 'inline-block', width: '12px', height: '12px', background: `${colors.yellow}40`, borderRadius: '2px', marginRight: '4px', verticalAlign: 'middle' }} />0.3-0.7 (moderate)</span>
            <span><span style={{ display: 'inline-block', width: '12px', height: '12px', background: `${colors.mint}30`, borderRadius: '2px', marginRight: '4px', verticalAlign: 'middle' }} />&lt; 0.3 (low)</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Tab 5: Ad Library ──────────────────────────────────────────────

function AdLibraryTab({ data }: { data: Record<string, unknown> }) {
  const ads = (data.ad_library || []) as Ad[]
  const [filter, setFilter] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)

  const filtered = ads
    .filter((a) => !filter || a.status === filter)
    .sort((a, b) => b.aggregate_score - a.aggregate_score)

  return (
    <div>
      {/* Filters */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {['', 'published', 'in_progress', 'discarded'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            style={filter === f ? s.filterActive : s.filterBtn}
          >
            {f || 'All'} ({f ? ads.filter((a) => a.status === f).length : ads.length})
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: colors.muted }}>No ads found</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {filtered.map((ad) => (
            <div
              key={ad.ad_id}
              onClick={() => setExpanded(expanded === ad.ad_id ? null : ad.ad_id)}
              style={s.adCard}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', color: colors.muted }}>{ad.ad_id}</span>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <StatusBadge status={ad.status} />
                  <Badge label={ad.aggregate_score.toFixed(1)} color={ad.aggregate_score >= 7 ? colors.mint : colors.yellow} />
                </div>
              </div>
              <p style={{ fontSize: '14px', color: colors.white, margin: 0, lineHeight: 1.4 }}>
                {ad.copy?.primary_text || ad.copy?.headline || '-'}
              </p>

              {ad.image_url && (
                <img
                  src={`/api${ad.image_url}`}
                  alt={`Ad ${ad.ad_id}`}
                  style={{ width: '100%', maxHeight: '480px', objectFit: 'contain' as const, borderRadius: radii.input, marginTop: '10px' }}
                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                />
              )}

              {expanded === ad.ad_id && (
                <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: `1px solid ${colors.muted}20`, fontSize: '13px', color: colors.white }}>
                  {ad.copy?.headline && <p><strong>Headline:</strong> {ad.copy.headline}</p>}
                  {ad.copy?.description && <p><strong>Description:</strong> {ad.copy.description}</p>}
                  {ad.copy?.cta_button && <p><strong>CTA:</strong> {ad.copy.cta_button}</p>}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', marginTop: '8px' }}>
                    {Object.entries(ad.scores).map(([dim, score]) => (
                      <div key={dim} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
                        <span style={{ color: colors.muted, fontSize: '11px' }}>{dim.replace(/_/g, ' ')}</span>
                        <span style={{ color: colors.white, fontWeight: 600 }}>{typeof score === 'number' ? score.toFixed(1) : '-'}</span>
                      </div>
                    ))}
                  </div>
                  {Object.keys(ad.rationale).length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      {Object.entries(ad.rationale).map(([dim, text]) => text && (
                        <p key={dim} style={{ fontSize: '12px', color: colors.muted, margin: '4px 0' }}>
                          <strong style={{ color: colors.white }}>{dim.replace(/_/g, ' ')}:</strong> {text}
                        </p>
                      ))}
                    </div>
                  )}
                  <p style={{ fontSize: '12px', color: colors.muted }}>Cycles: {ad.cycle_count}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tab 6: Token Economics ──────────────────────────────────────────

function TokenEconomicsTab({ data }: { data: Record<string, unknown> }) {
  const econ = (data.token_economics || {}) as Record<string, unknown>
  const byStage = (econ.by_stage || {}) as Record<string, number>
  const byModel = (econ.by_model || {}) as Record<string, number>
  const costPerPub = econ.cost_per_published as number | undefined

  return (
    <div>
      {costPerPub !== undefined && costPerPub > 0 && (
        <div style={{ textAlign: 'center', padding: '24px', background: colors.surface, borderRadius: radii.card, marginBottom: '24px' }}>
          <div style={{ fontSize: '36px', fontWeight: 700, color: colors.yellow, fontFamily: font.family }}>
            {costPerPub.toLocaleString()} tokens
          </div>
          <div style={{ fontSize: '14px', color: colors.muted, marginTop: '8px', fontFamily: font.family }}>
            Cost Per Published Ad
          </div>
        </div>
      )}

      <div style={s.section}>
        <h3 style={s.heading}>Cost by Pipeline Stage</h3>
        <CostBars data={byStage} barColor={colors.yellow} />
      </div>

      <div style={s.section}>
        <h3 style={s.heading}>Cost by Model</h3>
        <CostBars data={byModel} barColor={colors.cyan} />
      </div>
    </div>
  )
}

function CostBars({ data, barColor }: { data: Record<string, number>; barColor: string }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a)

  return (
    <div>
      {sorted.map(([label, tokens]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span style={{ width: '120px', fontSize: '12px', color: colors.muted, textAlign: 'right', fontFamily: font.family }}>
            {label}
          </span>
          <div style={{ flex: 1, height: '20px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${(tokens / total) * 100}%`, height: '100%', background: barColor, borderRadius: radii.input }} />
          </div>
          <span style={{ fontSize: '12px', color: colors.white, width: '60px', fontFamily: font.family }}>
            {tokens.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Tab 7: System Health ───────────────────────────────────────────

function SystemHealthTab({ data }: { data: Record<string, unknown> }) {
  const health = (data.system_health || {}) as Record<string, unknown>
  const spc = (health.spc || {}) as Record<string, unknown>
  const confidence = (health.confidence_stats || {}) as Record<string, unknown>
  const compliance = (health.compliance_stats || {}) as Record<string, unknown>

  const batchAvgs = (spc.batch_averages || []) as number[]
  const breaches = (spc.breach_indices || []) as number[]
  const breachSet = new Set(breaches)

  return (
    <div>
      {/* SPC */}
      <div style={s.section}>
        <h3 style={s.heading}>SPC Control Chart</h3>
        <div style={{ display: 'flex', gap: '32px', padding: '16px', background: colors.surface, borderRadius: radii.card }}>
          <StatBox label="Mean" value={spc.mean != null ? (spc.mean as number).toFixed(2) : '-'} />
          <StatBox label="UCL" value={spc.ucl != null ? (spc.ucl as number).toFixed(2) : '-'} color={colors.red} />
          <StatBox label="LCL" value={spc.lcl != null ? (spc.lcl as number).toFixed(2) : '-'} color={colors.yellow} />
          <StatBox label="Breaches" value={String(breaches.length)} color={colors.red} />
        </div>
        {batchAvgs.length > 0 && (
          <div style={{ marginTop: '12px' }}>
            <h4 style={{ ...s.heading, fontSize: '13px' }}>Batch Averages</h4>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {batchAvgs.map((avg, i) => (
                <span
                  key={i}
                  style={{
                    padding: '4px 10px',
                    borderRadius: radii.input,
                    fontSize: '12px',
                    fontFamily: font.family,
                    background: breachSet.has(i) ? `${colors.red}30` : colors.surface,
                    color: breachSet.has(i) ? colors.red : colors.white,
                    border: breachSet.has(i) ? `1px solid ${colors.red}60` : `1px solid ${colors.muted}20`,
                  }}
                >
                  B{i + 1}: {avg.toFixed(2)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Confidence routing */}
      {Object.keys(confidence).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Confidence Routing</h3>
          <div style={{ display: 'flex', gap: '32px', padding: '16px', background: colors.surface, borderRadius: radii.card }}>
            <StatBox label="Autonomous" value={`${confidence.autonomous_pct || 0}%`} color={colors.mint} />
            <StatBox label="Flagged" value={`${confidence.flagged_pct || 0}%`} color={colors.yellow} />
            <StatBox label="Human Required" value={`${confidence.human_required_pct || 0}%`} color={colors.red} />
            <StatBox label="Total" value={String(confidence.total || 0)} />
          </div>
        </div>
      )}

      {/* Compliance */}
      {Object.keys(compliance).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Compliance</h3>
          <div style={{ display: 'flex', gap: '32px', padding: '16px', background: colors.surface, borderRadius: radii.card }}>
            <StatBox label="Checked" value={String(compliance.total_checked || 0)} />
            <StatBox label="Passed" value={String(compliance.passed || 0)} color={colors.mint} />
            <StatBox label="Failed" value={String(compliance.failed || 0)} color={colors.red} />
            <StatBox label="Pass Rate" value={compliance.pass_rate ? `${((compliance.pass_rate as number) * 100).toFixed(0)}%` : '-'} />
          </div>
        </div>
      )}
    </div>
  )
}

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '20px', fontWeight: 700, color: color || colors.white, fontFamily: font.family }}>{value}</div>
      <div style={{ fontSize: '11px', color: colors.muted, fontFamily: font.family }}>{label}</div>
    </div>
  )
}

// ── Tab 8: Competitive Intel ───────────────────────────────────────

function CompetitiveIntelTab({ data }: { data: Record<string, unknown> }) {
  const ci = (data.competitive_intel || {}) as Record<string, unknown>

  if (Object.keys(ci).length === 0) {
    return <p style={{ color: colors.muted }}>No competitive data available</p>
  }

  const hookTypes = (ci.hook_type_counts || ci.hook_types || {}) as Record<string, number>
  const ctaStyles = (ci.cta_style_counts || ci.cta_styles || {}) as Record<string, number>
  const angles = (ci.emotional_angle_counts || ci.emotional_angles || {}) as Record<string, number>
  const competitors = (ci.competitors || []) as Record<string, unknown>[]
  const gaps = (ci.gap_analysis || ci.gaps || []) as string[]

  return (
    <div>
      <FrequencyBars title="Hook Types" data={hookTypes} barColor={colors.cyan} />
      <FrequencyBars title="CTA Styles" data={ctaStyles} barColor={colors.mint} />
      <FrequencyBars title="Emotional Angles" data={angles} barColor={colors.lightPurple} />

      {competitors.length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Competitors</h3>
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>Name</th>
                <th style={s.th}>Patterns</th>
              </tr>
            </thead>
            <tbody>
              {competitors.map((c, i) => (
                <tr key={i}>
                  <td style={s.td}>{String(c.name || c.competitor || '-')}</td>
                  <td style={s.td}>{String(c.pattern_count || c.patterns || '-')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {gaps.length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Gap Analysis</h3>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {gaps.map((g, i) => (
              <li key={i} style={{ color: colors.white, fontSize: '13px', marginBottom: '6px', fontFamily: font.family }}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function FrequencyBars({ title, data, barColor }: { title: string; data: Record<string, number>; barColor: string }) {
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a).slice(0, 10)
  const max = sorted[0]?.[1] || 1

  if (sorted.length === 0) return null

  return (
    <div style={{ marginBottom: '24px' }}>
      <h3 style={s.heading}>{title}</h3>
      {sorted.map(([label, count]) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <span style={{ width: '140px', fontSize: '12px', color: colors.muted, textAlign: 'right', fontFamily: font.family }}>
            {label}
          </span>
          <div style={{ flex: 1, height: '16px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${(count / max) * 100}%`, height: '100%', background: barColor, borderRadius: radii.input }} />
          </div>
          <span style={{ fontSize: '12px', color: colors.white, width: '30px', fontFamily: font.family }}>{count}</span>
        </div>
      ))}
    </div>
  )
}

// ── Styles ─────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: colors.ink,
    fontFamily: font.family,
    padding: '32px 20px',
    maxWidth: '1100px',
    margin: '0 auto',
  },
  header: { marginBottom: '24px' },
  backLink: { color: colors.cyan, cursor: 'pointer', fontSize: '13px' },
  title: {
    fontSize: '28px', fontWeight: 700, margin: '8px 0 4px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  tabBar: {
    display: 'flex', gap: '4px', marginBottom: '24px', overflowX: 'auto',
    borderBottom: `1px solid ${colors.muted}20`, paddingBottom: '0',
  },
  tab: {
    padding: '10px 16px', background: 'transparent', border: 'none',
    borderBottom: '2px solid transparent',
    color: colors.muted, cursor: 'pointer', fontSize: '13px', fontWeight: 500,
    fontFamily: font.family, whiteSpace: 'nowrap',
  },
  tabActive: {
    padding: '10px 16px', background: 'transparent', border: 'none',
    borderBottom: `2px solid ${colors.cyan}`,
    color: colors.cyan, cursor: 'pointer', fontSize: '13px', fontWeight: 600,
    fontFamily: font.family, whiteSpace: 'nowrap',
  },
  tabContent: { minHeight: '300px' },
  section: { marginBottom: '24px' },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px' },
  kpiCard: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px',
    textAlign: 'center',
  },
  cycleCard: {
    background: colors.surface,
    borderRadius: radii.input,
    padding: '14px 18px',
    fontFamily: font.family,
  },
  adCard: {
    background: colors.surface,
    borderRadius: radii.input,
    padding: '14px 18px',
    cursor: 'pointer',
    fontFamily: font.family,
  },
  filterBtn: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.muted}40`,
    background: 'transparent', color: colors.muted, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  filterActive: {
    padding: '6px 14px', borderRadius: radii.button, border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}20`, color: colors.cyan, cursor: 'pointer', fontSize: '12px', fontFamily: font.family,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: colors.surface,
    borderRadius: radii.input,
    overflow: 'hidden',
    fontSize: '13px',
    fontFamily: font.family,
  },
  th: {
    textAlign: 'left',
    padding: '10px 12px',
    color: colors.muted,
    fontWeight: 600,
    fontSize: '11px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    borderBottom: `1px solid ${colors.muted}20`,
  },
  td: {
    padding: '8px 12px',
    color: colors.white,
    borderBottom: `1px solid ${colors.muted}10`,
  },
}
