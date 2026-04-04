// Global Performance Dashboard — all-session pipeline data (8 tabs)
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import useMediaQuery from '../hooks/useMediaQuery'
import { fetchGlobalDashboard } from '../api/dashboard'
import { StatusBadge } from '../components/Badge'

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
  image_avg_score?: number
  image_scored_count?: number
  video_avg_score?: number
  video_scored_count?: number
  adherence_avg_score?: number
  adherence_scored_count?: number
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

// ── Tabs ───────────────────────────────────────────────────────────

const TABS = [
  { key: 'summary', label: 'Pipeline Summary' },
  { key: 'scoring', label: 'Scoring Methodology' },
  { key: 'iterations', label: 'Iteration Cycles' },
  { key: 'quality', label: 'Quality Trends' },
  { key: 'dimensions', label: 'Dimension Deep-Dive' },
  { key: 'costs', label: 'Token Economics' },
  { key: 'health', label: 'System Health' },
] as const

type TabKey = typeof TABS[number]['key']
const TIMEFRAMES = ['all', 'day', 'month', 'year'] as const
type TimeframeKey = typeof TIMEFRAMES[number]
const TIMEFRAME_LABELS: Record<TimeframeKey, string> = {
  all: 'All Time',
  day: 'Last 24 Hours',
  month: 'Last 30 Days',
  year: 'Last 12 Months',
}

// Theme is now handled globally via App.tsx ThemeToggle

// ── Main Component ─────────────────────────────────────────────────

export default function GlobalDashboard() {
  const isMobile = useMediaQuery('(max-width: 767px)')
  const isTablet = useMediaQuery('(max-width: 1024px)')
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  const activeTab = (searchParams.get('tab') as TabKey) || 'summary'
  const rawTimeframe = searchParams.get('timeframe')
  const timeframe: TimeframeKey = TIMEFRAMES.includes(rawTimeframe as TimeframeKey)
    ? (rawTimeframe as TimeframeKey)
    : 'all'

  useEffect(() => {
    setError(null)
    fetchGlobalDashboard(timeframe)
      .then((result) => setData(result))
      .catch((e) => setError(e.message))
  }, [timeframe])

  const setTab = (tab: TabKey) => setSearchParams({ tab, timeframe })
  const setTimeframe = (next: TimeframeKey) => setSearchParams({ tab: activeTab, timeframe: next })

  if (error) {
    return (
      <div style={s.pageBg}>
        <div style={{ ...s.pageInner, padding: isMobile ? '88px 16px 24px' : s.pageInner.padding }}>
          <p style={{ color: colors.red }}>{error}</p>
          <a href="/sessions" style={{ color: colors.cyan }}>Back to Sessions</a>
        </div>
      </div>
    )
  }

  if (!data) {
    return <div style={s.pageBg}><div style={{ ...s.pageInner, padding: isMobile ? '88px 16px 24px' : s.pageInner.padding }}><p style={{ color: colors.muted }}>Loading global dashboard...</p></div></div>
  }

  return (
    <div style={s.pageBg}>
      <div style={{ ...s.pageInner, padding: isMobile ? '88px 16px 24px' : s.pageInner.padding }}>
        {/* Header */}
        <div style={s.header}>
          <div style={{ ...s.headerTopRow, flexDirection: isMobile ? 'column' : s.headerTopRow.flexDirection, alignItems: isMobile ? 'stretch' : s.headerTopRow.alignItems }}>
            <div>
              <h1 style={s.dashboardTitle}>Dashboard</h1>
            </div>
            <div
              style={{
                ...s.timeframeGroup,
                width: isMobile ? '100%' : undefined,
                overflowX: isMobile ? 'auto' : undefined,
                flexWrap: isMobile ? 'nowrap' : s.timeframeGroup.flexWrap,
              }}
            >
              {TIMEFRAMES.map((option) => (
                <button
                  key={option}
                  onClick={() => setTimeframe(option)}
                  style={timeframe === option ? s.timeframeBtnActive : s.timeframeBtn}
                >
                  {TIMEFRAME_LABELS[option]}
                </button>
              ))}
            </div>
          </div>
          <h1 style={{ ...s.title, fontSize: isMobile ? '24px' : s.title.fontSize }}>Global Dashboard</h1>
          <p style={{ color: colors.muted, fontSize: '13px', margin: 0, maxWidth: '720px', lineHeight: '1.6' }}>
            Aggregated view of every ad generation session. Metrics are read from the
            global decision ledger — the append-only log of every generation, evaluation,
            regeneration, and publish event across all sessions. Use this to track overall
            pipeline efficiency, quality trends, and cost-per-publishable-ad over time.
          </p>
          <p style={s.timeframeSummary}>
            Showing <strong>{TIMEFRAME_LABELS[timeframe]}</strong> of pipeline activity.
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
          {activeTab === 'summary' && <PipelineSummaryTab data={data} isMobile={isMobile} />}
          {activeTab === 'iterations' && <IterationCyclesTab data={data} isMobile={isMobile} />}
          {activeTab === 'quality' && <QualityTrendsTab data={data} isMobile={isMobile} />}
          {activeTab === 'dimensions' && <DimensionDeepDiveTab data={data} isMobile={isMobile} isTablet={isTablet} />}
          {activeTab === 'costs' && <TokenEconomicsTab data={data} isMobile={isMobile} />}
          {activeTab === 'health' && <SystemHealthTab data={data} isMobile={isMobile} />}
          {activeTab === 'scoring' && <ScoringMethodologyTab />}
        </div>
      </div>
    </div>
  )
}

// ── Tab 1: Pipeline Summary ────────────────────────────────────────

function PipelineSummaryTab({ data, isMobile }: { data: Record<string, unknown>; isMobile: boolean }) {
  const ps = (data.pipeline_summary || {}) as PipelineSummary
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const metrics = [
    { label: 'Ads Generated', value: ps.total_ads_generated ?? 0, color: colors.white,
      tip: 'Total ad variants created across all sessions and cycles, including regeneration attempts.' },
    { label: 'Ads Published', value: ps.total_ads_published ?? 0, color: colors.mint,
      tip: 'Ads that scored above the quality threshold (7.0+) and passed all 3 compliance layers.' },
    { label: 'Publish Rate', value: ps.publish_rate ? `${(ps.publish_rate * 100).toFixed(0)}%` : '0%', color: colors.cyan,
      tip: 'Percentage of generated ads that met the publish threshold. Higher rates mean better briefs and fewer wasted tokens.' },
    { label: 'Avg Copy Score', value: ps.avg_score?.toFixed(1) ?? '0.0', color: colors.yellow,
      tip: 'Mean weighted copy score across 5 dimensions (Clarity, Value Prop, CTA, Brand Voice, Emotional Resonance) for published ads. Image and video quality are not scored.' },
    { label: 'Total Batches', value: ps.total_batches ?? 0, color: colors.white,
      tip: 'Number of batch processing rounds completed. Each batch generates, evaluates, and optionally regenerates up to 10 ads.' },
    { label: 'Total Tokens', value: (ps.total_tokens ?? 0).toLocaleString(), color: colors.white,
      tip: 'Sum of input + output tokens consumed across all LLM calls (generation, evaluation, regeneration) and image API calls.' },
    { label: 'Total Cost', value: `$${(ps.total_cost_usd ?? 0).toFixed(2)}`, color: colors.yellow,
      tip: 'Estimated spend across app sessions, based on the session summaries stored for each pipeline run.' },
    { label: 'Ads Discarded', value: ps.total_ads_discarded ?? 0, color: colors.red,
      tip: 'Ads that failed to meet the quality threshold after all regeneration cycles, or were rejected by compliance filters.' },
    { label: 'Image Avg', value: ps.image_avg_score ? ps.image_avg_score.toFixed(1) : '—', color: colors.cyan,
      tip: `Average image quality score across ${ps.image_scored_count ?? 0} scored images (visual clarity, brand consistency, emotional impact, coherence, platform fit).` },
    { label: 'Video Avg', value: ps.video_avg_score ? ps.video_avg_score.toFixed(1) : '—', color: colors.cyan,
      tip: `Average video quality score across ${ps.video_scored_count ?? 0} scored videos (hook strength, visual quality, narrative flow, coherence, UGC authenticity).` },
    { label: 'Adherence Avg', value: ps.adherence_avg_score ? ps.adherence_avg_score.toFixed(1) : '—', color: colors.mint,
      tip: `Average brief adherence score across ${ps.adherence_scored_count ?? 0} scored ads (audience match, goal alignment, persona fit, message delivery, format adherence).` },
  ]

  return (
    <div style={s.kpiGrid}>
      {metrics.map((m, i) => (
        <div
          key={m.label}
          style={{ ...s.kpiCard, ...(hoveredIdx === i ? s.kpiCardHover : {}) }}
          onMouseEnter={() => setHoveredIdx(i)}
          onMouseLeave={() => setHoveredIdx(null)}
        >
          <div style={{ fontSize: '28px', fontWeight: 700, color: m.color, fontFamily: font.family }}>
            {String(m.value)}
          </div>
          <div style={{ fontSize: '12px', color: colors.muted, marginTop: '6px', fontFamily: font.family }}>
            {m.label}
          </div>
          {hoveredIdx === i && (
            <div style={{ ...s.kpiTooltip, width: isMobile ? 'min(240px, calc(100vw - 48px))' : s.kpiTooltip.width }}>{m.tip}</div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Tab 2: Iteration Cycles ────────────────────────────────────────

function IterationCyclesTab({ data, isMobile }: { data: Record<string, unknown>; isMobile: boolean }) {
  const cycles = (data.iteration_cycles || []) as IterationCycle[]

  if (cycles.length === 0) return <p style={{ color: colors.muted }}>No iteration data available</p>

  return (
    <div>
      <h3 style={s.heading}>How To Read Iteration Cycles</h3>
      <p style={s.sectionDescription}>
        Each card shows one regeneration pass for an ad. <strong>Before</strong> is the score prior to feedback,
        <strong> After</strong> is the score after revision, and the green or red number in the middle is the net
        change. <strong>Weakest</strong> identifies the lowest-scoring dimension that likely triggered the rewrite,
        helping you see which dimensions most often limit publishability across the whole pipeline.
      </p>
      <div style={s.cycleGrid}>
        {cycles.map((c) => {
          const delta = c.score_after - c.score_before
          const improved = delta > 0
          return (
            <div key={c.ad_id} style={s.cycleCard}>
              <div style={s.cycleHeader}>
                <span style={s.cycleAdId} title={c.ad_id}>{c.ad_id}</span>
                <StatusBadge status={c.action_taken} />
              </div>
              <div style={{ ...s.cycleMetrics, gridTemplateColumns: isMobile ? '1fr' : s.cycleMetrics.gridTemplateColumns }}>
                <div style={s.cycleMetricBlock}>
                  <div style={s.cycleMetricLabel}>Before</div>
                  <div style={s.cycleMetricValue}>
                    {c.score_before.toFixed(1)}
                  </div>
                </div>
                <div style={{ ...s.cycleDelta, color: improved ? colors.mint : colors.red }}>
                  {improved ? '+' : ''}{delta.toFixed(1)}
                </div>
                <div style={s.cycleMetricBlock}>
                  <div style={s.cycleMetricLabel}>After</div>
                  <div style={s.cycleMetricValue}>
                    {c.score_after.toFixed(1)}
                  </div>
                </div>
              </div>
              <div style={s.cycleFooter}>
                <div style={s.cycleMetricLabel}>Weakest</div>
                <div style={s.cycleWeakest}>{c.weakest_dimension.replace(/_/g, ' ')}</div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Tab 3: Quality Trends ──────────────────────────────────────────

function ScoreDistribution({ title, distribution, color }: { title: string; distribution: number[]; color: string }) {
  const total = distribution.reduce((a, b) => a + b, 0)
  if (total === 0) return null
  const max = Math.max(...distribution, 1)

  return (
    <div style={{ marginBottom: '20px' }}>
      <h4 style={{ fontSize: '13px', fontWeight: 600, color: colors.white, margin: '0 0 8px', fontFamily: font.family }}>{title} <span style={{ color: colors.muted, fontWeight: 400 }}>({total} scored)</span></h4>
      <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '80px' }}>
        {distribution.map((count, i) => (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', textAlign: 'center' }}>
            <div
              style={{
                height: `${Math.round((count / max) * 70)}px`,
                width: '100%',
                background: count > 0 ? color : `${colors.muted}20`,
                borderRadius: '4px 4px 0 0',
                minHeight: count > 0 ? '4px' : '0px',
              }}
            />
            <div style={{ fontSize: '10px', color: colors.muted, marginTop: '2px' }}>{i}-{i + 1}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function QualityTrendsTab({ data }: { data: Record<string, unknown> }) {
  const trends = (data.quality_trends || {}) as Record<string, unknown>
  const batchScores = (trends.batch_scores || []) as BatchScore[]
  const distribution = (trends.score_distribution || []) as number[]
  const imageDistribution = (trends.image_score_distribution || []) as number[]
  const videoDistribution = (trends.video_score_distribution || []) as number[]
  const adherenceDistribution = (trends.adherence_score_distribution || []) as number[]

  return (
    <div>
      {/* Batch scores table */}
      <div style={s.section}>
        <h3 style={s.heading}>Batch Scores</h3>
        <p style={s.sectionDescription}>
          This table summarizes pipeline performance one batch at a time. Each row represents a batch of ads
          processed together, usually 10 at a time. <strong>Avg Score</strong> is the mean quality score for that batch,
          <strong> Threshold</strong> is the publish cutoff in effect for that batch, <strong>Published</strong> shows how many
          ads cleared that bar, and <strong>Pub Rate</strong> shows the percentage that made it through. <strong>Tokens</strong>
          helps you compare quality output against model spend, so you can spot batches that were expensive but underperformed.
        </p>
        {batchScores.length === 0 ? (
          <p style={{ color: colors.muted }}>No batch data yet</p>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                {['Batch', 'Avg Copy Score', 'Threshold', 'Published', 'Generated', 'Pub Rate', 'Tokens'].map((h) => (
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

      {/* Score distributions — all content types */}
      <div style={s.section}>
        <h3 style={s.heading}>Score Distributions</h3>
        <p style={s.sectionDescription}>
          How scores are distributed across all scored content. Each bar represents a score bucket (e.g., 7-8).
          Taller bars mean more ads scored in that range. Compare across content types to see where each type lands.
        </p>
        <ScoreDistribution title="Copy Quality" distribution={distribution} color={colors.cyan} />
        <ScoreDistribution title="Brief Adherence" distribution={adherenceDistribution} color={colors.mint} />
        <ScoreDistribution title="Image Quality" distribution={imageDistribution} color={colors.yellow} />
        <ScoreDistribution title="Video Quality" distribution={videoDistribution} color={colors.white} />
      </div>
    </div>
  )
}

// ── Tab 4: Dimension Deep-Dive ─────────────────────────────────────

function DimensionGrid({
  title,
  description,
  trends,
  isMobile,
  isTablet,
}: {
  title: string
  description: string
  trends: Record<string, number[]>
  isMobile: boolean
  isTablet: boolean
}) {
  const entries = Object.entries(trends).filter(([, vals]) => (vals as number[]).length > 0)
  if (entries.length === 0) return null

  const avgs = entries.map(([dim, vals]) => {
    const arr = vals as number[]
    return { dim, avg: arr.reduce((a, b) => a + b, 0) / arr.length, count: arr.length }
  })

  return (
    <div style={s.section}>
      <h3 style={s.heading}>{title}</h3>
      <p style={s.sectionDescription}>{description}</p>
      <div
        style={{
          ...s.dimensionAvgGrid,
          gridTemplateColumns: isMobile
            ? 'repeat(2, minmax(0, 1fr))'
            : isTablet
              ? 'repeat(3, minmax(0, 1fr))'
              : s.dimensionAvgGrid.gridTemplateColumns,
        }}
      >
        {avgs.map(({ dim, avg, count }) => (
          <div key={dim} style={s.dimensionAvgCard}>
            <div style={{ fontSize: '22px', fontWeight: 700, color: avg >= 7 ? colors.mint : avg >= 5 ? colors.yellow : colors.red, fontFamily: font.family }}>
              {avg.toFixed(1)}
            </div>
            <div style={{ fontSize: '12px', color: colors.muted, marginTop: '4px', fontFamily: font.family }}>
              {dim.replace(/_/g, ' ')}
            </div>
            <div style={{ fontSize: '10px', color: colors.muted, fontFamily: font.family }}>n={count}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function DimensionDeepDiveTab({ data, isMobile, isTablet }: { data: Record<string, unknown>; isMobile: boolean; isTablet: boolean }) {
  const dd = (data.dimension_deep_dive || {}) as Record<string, unknown>
  const dimTrends = (dd.dimension_trends || {}) as Record<string, number[]>
  const imageTrends = (dd.image_dimension_trends || {}) as Record<string, number[]>
  const videoTrends = (dd.video_dimension_trends || {}) as Record<string, number[]>
  const adherenceTrends = (dd.adherence_dimension_trends || {}) as Record<string, number[]>
  const corrMatrix = (dd.correlation_matrix || {}) as Record<string, Record<string, number>>
  const dimensions = Object.keys(dimTrends)

  const corrColor = (r: number) => {
    const abs = Math.abs(r)
    if (abs >= 0.7) return `${colors.red}40`
    if (abs >= 0.3) return `${colors.yellow}40`
    return `${colors.mint}30`
  }

  return (
    <div>
      <DimensionGrid
        title="Copy Quality"
        description="Average score for each of the five copy evaluation dimensions across all scored ads."
        trends={dimTrends}
        isMobile={isMobile}
        isTablet={isTablet}
      />
      <DimensionGrid
        title="Brief Adherence"
        description="How well ads follow the creative brief — audience targeting, persona tone, key message delivery, and format compliance."
        trends={adherenceTrends}
        isMobile={isMobile}
        isTablet={isTablet}
      />
      <DimensionGrid
        title="Image Quality"
        description="Visual quality scores for generated ad images — clarity, brand consistency, emotional impact, copy coherence, and platform fit."
        trends={imageTrends}
        isMobile={isMobile}
        isTablet={isTablet}
      />
      <DimensionGrid
        title="Video Quality"
        description="Video quality scores — hook strength, visual quality, narrative flow, copy coherence, and UGC authenticity."
        trends={videoTrends}
        isMobile={isMobile}
        isTablet={isTablet}
      />

      {/* Correlation matrix (copy dimensions only — others will have too few data points initially) */}
      {dimensions.length > 0 && Object.keys(corrMatrix).length > 0 && (
        <div style={s.section}>
          <h3 style={s.heading}>Copy Correlation Matrix</h3>
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

// ── Tab 6: Token Economics ──────────────────────────────────────────

function TokenEconomicsTab({ data, isMobile }: { data: Record<string, unknown>; isMobile: boolean }) {
  const econ = (data.token_economics || {}) as Record<string, unknown>
  const byStage = (econ.by_stage || {}) as Record<string, number>
  const byModel = (econ.by_model || {}) as Record<string, number>
  const costPerPub = econ.cost_per_published as number | undefined

  return (
    <div>
      <h3 style={s.heading}>How To Read Token Economics</h3>
      <p style={s.sectionDescription}>
        This tab explains where model spend is going across the pipeline. It helps you compare output quality against
        token consumption so you can spot expensive stages, understand which models are driving cost, and estimate how
        much compute it takes to produce one publishable ad.
      </p>
      {costPerPub !== undefined && costPerPub > 0 && (
        <div style={{ textAlign: 'center', padding: '24px', background: colors.surface, borderRadius: radii.card, marginBottom: '24px' }}>
          <div style={{ fontSize: '36px', fontWeight: 700, color: colors.yellow, fontFamily: font.family }}>
            {costPerPub.toLocaleString()} tokens
          </div>
          <div style={{ fontSize: '14px', color: colors.muted, marginTop: '8px', fontFamily: font.family }}>
            Cost Per Published Ad
          </div>
          <p style={{ ...s.sectionDescription, margin: '10px auto 0', textAlign: 'center', maxWidth: '620px' }}>
            This is the average token cost required to get one ad over the publish threshold. Lower is more efficient;
            higher means the system is spending more generation, evaluation, or regeneration effort per successful ad.
          </p>
        </div>
      )}

      <div style={s.section}>
        <h3 style={s.heading}>Cost by Pipeline Stage</h3>
        <p style={s.sectionDescription}>
          Shows which parts of the workflow are consuming the most tokens, such as generation, evaluation, or
          regeneration. Use this to identify stages where quality gains may not justify the extra spend.
        </p>
        <CostBars data={byStage} barColor={colors.yellow} isMobile={isMobile} />
      </div>

      <div style={s.section}>
        <h3 style={s.heading}>Cost by Model</h3>
        <p style={s.sectionDescription}>
          Compares spend by model family. This is useful for checking whether higher-cost models are concentrated in
          borderline ads and whether the current routing strategy is using expensive tokens where they actually help.
        </p>
        <CostBars data={byModel} barColor={colors.cyan} isMobile={isMobile} />
      </div>
    </div>
  )
}

function CostBars({
  data,
  barColor,
  isMobile,
}: {
  data: Record<string, number>
  barColor: string
  isMobile: boolean
}) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1
  const sorted = Object.entries(data).sort(([, a], [, b]) => b - a)

  return (
    <div>
      {sorted.map(([label, tokens]) => (
        <div
          key={label}
          style={{
            display: 'flex',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
            marginBottom: '8px',
          }}
        >
          <span style={{ width: isMobile ? '100%' : '120px', fontSize: '12px', color: colors.muted, textAlign: isMobile ? 'left' : 'right', fontFamily: font.family }}>
            {label}
          </span>
          <div style={{ flex: 1, height: '20px', background: `${colors.muted}20`, borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ width: `${(tokens / total) * 100}%`, height: '100%', background: barColor, borderRadius: radii.input }} />
          </div>
          <span style={{ fontSize: '12px', color: colors.white, width: isMobile ? '100%' : '60px', fontFamily: font.family, textAlign: isMobile ? 'right' : 'left' }}>
            {tokens.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Tab 7: System Health ───────────────────────────────────────────

function SystemHealthTab({ data, isMobile }: { data: Record<string, unknown>; isMobile: boolean }) {
  const health = (data.system_health || {}) as Record<string, unknown>
  const spc = (health.spc || {}) as Record<string, unknown>
  const confidence = (health.confidence_stats || {}) as Record<string, unknown>
  const compliance = (health.compliance_stats || {}) as Record<string, unknown>

  const batchAvgs = (spc.batch_averages || []) as number[]
  const breaches = (spc.breach_indices || []) as number[]
  const breachSet = new Set(breaches)

  return (
    <div>
      <h3 style={s.heading}>How To Read System Health</h3>
      <p style={s.sectionDescription}>
        This tab monitors whether the pipeline is behaving consistently and safely over time. It combines statistical
        process control, confidence routing, and compliance outcomes so you can see whether quality is stable, whether
        ads are being trusted appropriately, and whether safety checks are catching problems before publish.
      </p>
      {/* SPC */}
      <div style={s.section}>
        <h3 style={s.heading}>SPC Control Chart</h3>
        <p style={s.sectionDescription}>
          SPC tracks whether batch quality is staying within a normal operating range. <strong>Mean</strong> is the
          average batch score, while <strong>UCL</strong> and <strong>LCL</strong> are the upper and lower control
          limits. A breach suggests the evaluator or generation system may be drifting, improving unusually fast, or
          degrading unexpectedly.
        </p>
        <div
          style={{
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '16px',
            padding: '16px',
            background: colors.surface,
            borderRadius: radii.card,
          }}
        >
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
          <p style={s.sectionDescription}>
            Confidence routing shows how often the system can act autonomously versus how often it should escalate.
            High autonomous rates suggest stable evaluator confidence; high flagged or human-required rates can indicate
            ambiguous ads, weak prompts, or a need for tighter calibration.
          </p>
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
          <p style={s.sectionDescription}>
            Compliance summarizes how many ads were checked by the safety pipeline and how many passed. This helps you
            see whether policy failures are rare exceptions or a recurring quality issue that needs upstream prompt or
            filtering changes.
          </p>
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

// ── Tab: Scoring Methodology ──────────────────────────────────────

function ScoringCategory({ title, color, description, dimensions }: {
  title: string
  color: string
  description: string
  dimensions: { name: string; low: string; mid: string; high: string }[]
}) {
  return (
    <div style={{ ...s.section, background: colors.surface, borderRadius: radii.card, padding: '20px 24px' }}>
      <h3 style={{ ...s.heading, color, margin: '0 0 4px' }}>{title}</h3>
      <p style={{ ...s.sectionDescription, margin: '0 0 16px' }}>{description}</p>
      <table style={{ ...s.table, background: 'transparent' }}>
        <thead>
          <tr>
            <th style={{ ...s.th, width: '160px' }}>Dimension</th>
            <th style={{ ...s.th, color: colors.red }}>Low (1-3)</th>
            <th style={{ ...s.th, color: colors.yellow }}>Mid (4-6)</th>
            <th style={{ ...s.th, color: colors.mint }}>High (7-10)</th>
          </tr>
        </thead>
        <tbody>
          {dimensions.map((d) => (
            <tr key={d.name}>
              <td style={{ ...s.td, fontWeight: 600, color: colors.white }}>{d.name}</td>
              <td style={{ ...s.td, fontSize: '12px' }}>{d.low}</td>
              <td style={{ ...s.td, fontSize: '12px' }}>{d.mid}</td>
              <td style={{ ...s.td, fontSize: '12px' }}>{d.high}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ScoringMethodologyTab() {
  return (
    <div>
      <h3 style={s.heading}>Scoring Methodology</h3>
      <p style={s.sectionDescription}>
        Every ad is evaluated across up to 4 scoring categories, each with 5 dimensions scored 1-10 by Gemini Flash.
        Copy quality and brief adherence are scored for all ads. Image and video quality are scored only when media is present.
        Scores are <strong>not gates</strong> — they measure quality for analytics and comparison, not for publish decisions.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <ScoringCategory
          title="Copy Quality"
          color={colors.cyan}
          description="Is this a good ad? Evaluates the text independent of the brief — pure ad copy quality."
          dimensions={[
            { name: 'Clarity', low: 'Confusing message, unclear value', mid: 'Understandable but generic', high: 'Instantly clear, compelling' },
            { name: 'Value Proposition', low: 'No benefit stated', mid: 'Benefit mentioned but weak', high: 'Specific, differentiated benefit' },
            { name: 'Call to Action', low: 'No CTA or wrong action', mid: 'Generic CTA (Learn More)', high: 'Urgent, specific, conversion-driving' },
            { name: 'Brand Voice', low: 'Wrong tone for brand', mid: 'Generic tone', high: 'Unmistakably on-brand voice' },
            { name: 'Emotional Resonance', low: 'Flat, no emotional hook', mid: 'Mild engagement', high: 'Deeply connects with audience pain/aspiration' },
          ]}
        />

        <ScoringCategory
          title="Brief Adherence"
          color={colors.mint}
          description="Did the ad do what I asked? Measures compliance with the session's creative brief — audience, persona, key message, format."
          dimensions={[
            { name: 'Audience Match', low: 'Wrong audience entirely', mid: 'Ambiguous targeting', high: 'Speaks directly to configured audience' },
            { name: 'Goal Alignment', low: 'Wrong campaign goal', mid: 'Partially aligned', high: 'Perfectly serves the goal' },
            { name: 'Persona Fit', low: 'Generic tone, ignores persona', mid: 'Partially matches persona', high: 'Nails the persona voice and emotional state' },
            { name: 'Message Delivery', low: 'Key message absent', mid: 'Vaguely implied', high: 'Key message is central to the ad' },
            { name: 'Format Adherence', low: 'Wrong format entirely', mid: 'Partially matches brief style', high: 'Perfect format match (UGC, testimonial, etc.)' },
          ]}
        />

        <ScoringCategory
          title="Image Quality"
          color={colors.yellow}
          description="How good is the image as a social ad creative? Evaluated strictly — AI-generated images are held to high standards. Average scores of 5-7 are expected."
          dimensions={[
            { name: 'Visual Clarity', low: 'Cluttered, confusing subject', mid: 'Subject identifiable but generic', high: 'Striking composition, instant focal point' },
            { name: 'Brand Consistency', low: 'Could be any brand', mid: 'Generic imagery', high: 'Unmistakably on-brand aesthetic' },
            { name: 'Emotional Impact', low: 'Flat stock-photo energy', mid: 'Mildly pleasant but forgettable', high: 'Emotionally compelling, stops the scroll' },
            { name: 'Copy-Image Coherence', low: 'Image unrelated to copy', mid: 'Loosely related theme', high: 'Image and copy tell the exact same story' },
            { name: 'Platform Fit', low: 'Bad on mobile, tiny details', mid: 'Acceptable but not scroll-stopping', high: 'Designed for thumb-zone, high contrast' },
          ]}
        />

        <ScoringCategory
          title="Video Quality"
          color={colors.white}
          description="How good is the video as a social ad creative? Uses Gemini's native video understanding to analyze motion, pacing, and authenticity."
          dimensions={[
            { name: 'Hook Strength', low: 'Slow start, nothing compelling', mid: 'Acceptable but skippable', high: 'First 2s stop the scroll immediately' },
            { name: 'Visual Quality', low: 'Glitchy, artifacts, uncanny', mid: 'Passable but obvious AI', high: 'Smooth, natural lighting, professional' },
            { name: 'Narrative Flow', low: 'Disjointed, random scenes', mid: 'Basic progression, no arc', high: 'Compelling mini-story with clear CTA' },
            { name: 'Copy-Video Coherence', low: 'Video ignores ad text', mid: 'Loosely related', high: 'Video perfectly amplifies the message' },
            { name: 'UGC Authenticity', low: 'Obviously corporate/AI', mid: 'Neutral — neither real nor fake', high: 'Feels like genuine user content' },
          ]}
        />
      </div>

      <div style={{ ...s.section, marginTop: '24px' }}>
        <h3 style={s.heading}>How Scores Are Used</h3>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: '16px' }}>
          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '16px' }}>
            <h4 style={{ color: colors.mint, fontSize: '14px', margin: '0 0 8px', fontFamily: font.family }}>Publish Gate (existing)</h4>
            <p style={{ color: colors.muted, fontSize: '13px', margin: 0, lineHeight: 1.5, fontFamily: font.family }}>
              Copy quality score of 7.0+ required to publish. Binary image/video attribute checks must pass.
              These gates decide <strong>if</strong> an ad ships.
            </p>
          </div>
          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '16px' }}>
            <h4 style={{ color: colors.cyan, fontSize: '14px', margin: '0 0 8px', fontFamily: font.family }}>Quality Analytics (new)</h4>
            <p style={{ color: colors.muted, fontSize: '13px', margin: 0, lineHeight: 1.5, fontFamily: font.family }}>
              20-dimension scoring (copy + adherence + image + video) runs after publish. Measures <strong>how good</strong> the ad is
              for dashboards, trend tracking, and cross-session comparison. Does not block publishing.
            </p>
          </div>
        </div>
      </div>

      <div style={{ ...s.section, marginTop: '24px' }}>
        <h3 style={s.heading}>How Gemini Scores Each Content Type</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '20px 24px' }}>
            <h4 style={{ color: colors.cyan, fontSize: '14px', margin: '0 0 8px', fontFamily: font.family }}>Copy Scoring — Text-Only</h4>
            <p style={{ color: colors.muted, fontSize: '13px', margin: '0 0 8px', lineHeight: 1.6, fontFamily: font.family }}>
              Uses <strong>Gemini 2.0 Flash</strong> with a text-only prompt. The ad copy (headline, primary text, CTA) is sent alongside
              the evaluation rubric. The LLM reads the text and scores each dimension with a chain-of-thought rationale.
            </p>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, fontFamily: font.family }}>
              Cost: ~500-800 tokens per ad (~$0.0001)
            </p>
          </div>

          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '20px 24px' }}>
            <h4 style={{ color: colors.yellow, fontSize: '14px', margin: '0 0 8px', fontFamily: font.family }}>Image Scoring — Multimodal</h4>
            <p style={{ color: colors.muted, fontSize: '13px', margin: '0 0 8px', lineHeight: 1.6, fontFamily: font.family }}>
              Uses <strong>Gemini 2.0 Flash multimodal</strong>. The image file is uploaded to Google's servers, then sent alongside
              the text prompt in a single API call. Gemini processes the actual pixel data — it can identify subjects, composition,
              colors, text overlays, facial expressions, lighting quality, and aspect ratio usage. It does <em>not</em> receive a
              text description of the image — it sees the raw pixels the same way a human reviewer would.
            </p>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, fontFamily: font.family }}>
              Cost: ~2,000-3,000 tokens per image (~$0.0004) — image pixels are tokenized (~1,500 tokens) + text prompt (~500 tokens)
            </p>
          </div>

          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '20px 24px' }}>
            <h4 style={{ color: colors.white, fontSize: '14px', margin: '0 0 8px', fontFamily: font.family }}>Video Scoring — Native Video Understanding</h4>
            <p style={{ color: colors.muted, fontSize: '13px', margin: '0 0 8px', lineHeight: 1.6, fontFamily: font.family }}>
              Uses <strong>Gemini 2.0 Flash with native video understanding</strong>. The video file (MP4, 4-8 seconds) is uploaded
              and processed by Google's backend (frame extraction + audio analysis). Gemini analyzes:
            </p>
            <ul style={{ color: colors.muted, fontSize: '13px', margin: '0 0 8px', lineHeight: 1.6, fontFamily: font.family, paddingLeft: '20px' }}>
              <li><strong>Visual frames</strong> — Sampled throughout the video (~1fps), understands subjects, motion, transitions, lighting changes</li>
              <li><strong>Temporal reasoning</strong> — Understands sequence and pacing: "what happens in the first 2 seconds?" vs "how does it end?" — this is how hook strength is evaluated</li>
              <li><strong>Motion quality</strong> — Detects artifacts, flickering, unnatural physics, jerky motion that only exist in video</li>
              <li><strong>Audio</strong> (if present) — Hears dialogue, music, sound effects and evaluates whether they match the visual content</li>
            </ul>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, fontFamily: font.family }}>
              Cost: ~4,000-8,000 tokens per video (~$0.001) — multiple video frames tokenized (~3,000-6,000) + audio + text prompt
            </p>
          </div>

        </div>
      </div>

      <div style={{ ...s.section, marginTop: '24px' }}>
        <h3 style={s.heading}>Why Scores May Cluster</h3>
        <p style={{ color: colors.muted, fontSize: '13px', lineHeight: 1.6, fontFamily: font.family, margin: '0 0 12px' }}>
          You may notice image and video scores clustering in a narrow range (e.g., most images scoring 6-7). This is expected for three reasons:
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: '12px' }}>
          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '16px' }}>
            <h4 style={{ color: colors.white, fontSize: '13px', margin: '0 0 6px', fontFamily: font.family }}>Same Pipeline</h4>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, lineHeight: 1.5, fontFamily: font.family }}>
              All images come from the same generation model with similar prompts and brand constraints. There's limited natural variation to differentiate.
            </p>
          </div>
          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '16px' }}>
            <h4 style={{ color: colors.white, fontSize: '13px', margin: '0 0 6px', fontFamily: font.family }}>LLM Anchoring</h4>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, lineHeight: 1.5, fontFamily: font.family }}>
              LLMs naturally gravitate toward the center of whatever range the prompt emphasizes. The rubric calibrates for a 5-6 average, but some anchoring remains.
            </p>
          </div>
          <div style={{ background: colors.surface, borderRadius: radii.card, padding: '16px' }}>
            <h4 style={{ color: colors.white, fontSize: '13px', margin: '0 0 6px', fontFamily: font.family }}>No Visual Reference</h4>
            <p style={{ color: colors.muted, fontSize: '12px', margin: 0, lineHeight: 1.5, fontFamily: font.family }}>
              Gemini scores each image in isolation — it can't see "here's what a 3 looks like vs a 9." Few-shot scoring with reference images would improve differentiation but at higher token cost.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Styles ─────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  pageBg: {
    minHeight: '100vh',
    width: '100%',
    background: colors.ink,
    fontFamily: font.family,
  },
  pageInner: {
    maxWidth: '1100px',
    margin: '0 auto',
    padding: '84px 20px 32px',
  },
  header: { marginBottom: '24px' },
  headerTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '16px',
    flexWrap: 'wrap',
    marginBottom: '4px',
  },
  dashboardTitle: {
    fontSize: '28px',
    fontWeight: 700,
    color: colors.white,
    margin: 0,
    fontFamily: font.family,
  },
  title: {
    fontSize: '28px', fontWeight: 700, margin: '8px 0 4px',
    background: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  timeframeGroup: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  timeframeBtn: {
    padding: '8px 12px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  timeframeBtnActive: {
    padding: '8px 12px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}18`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  timeframeSummary: {
    color: colors.muted,
    fontSize: '12px',
    margin: '10px 0 0',
    fontFamily: font.family,
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
  sectionDescription: {
    color: colors.muted,
    fontSize: '13px',
    lineHeight: '1.6',
    margin: '0 0 16px',
    maxWidth: '780px',
    fontFamily: font.family,
  },
  dimensionAvgGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, minmax(0, 1fr))',
    gap: '12px',
  },
  dimensionAvgCard: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px 16px',
    minHeight: '108px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
  },
  heading: { fontSize: '16px', fontWeight: 600, color: colors.white, margin: '0 0 12px', fontFamily: font.family },
  kpiGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '12px' },
  kpiCard: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px',
    textAlign: 'center',
    position: 'relative',
    cursor: 'default',
    transition: 'border-color 0.15s ease',
    border: '1px solid transparent',
  },
  kpiCardHover: {
    borderColor: `${colors.cyan}60`,
  },
  kpiTooltip: {
    position: 'absolute',
    left: '50%',
    bottom: 'calc(100% + 8px)',
    transform: 'translateX(-50%)',
    background: colors.ink,
    border: `1px solid ${colors.muted}40`,
    borderRadius: radii.input,
    padding: '10px 14px',
    fontSize: '12px',
    lineHeight: '1.5',
    color: colors.white,
    fontFamily: font.family,
    width: '240px',
    textAlign: 'left',
    zIndex: 10,
    boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
  },
  cycleGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '10px',
    alignItems: 'start',
  },
  cycleCard: {
    background: colors.surface,
    borderRadius: radii.input,
    padding: '12px 14px',
    fontFamily: font.family,
    minWidth: 0,
  },
  cycleHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '8px',
  },
  cycleAdId: {
    fontSize: '12px',
    color: colors.muted,
    minWidth: 0,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  cycleMetrics: {
    display: 'grid',
    gridTemplateColumns: '1fr auto 1fr',
    gap: '10px',
    alignItems: 'center',
    marginTop: '10px',
  },
  cycleMetricBlock: {
    textAlign: 'center',
    minWidth: 0,
  },
  cycleMetricLabel: {
    fontSize: '11px',
    color: colors.muted,
  },
  cycleMetricValue: {
    fontSize: '18px',
    fontWeight: 700,
    color: colors.white,
    fontFamily: font.family,
  },
  cycleDelta: {
    fontSize: '16px',
    fontFamily: font.family,
    fontWeight: 700,
    whiteSpace: 'nowrap',
  },
  cycleFooter: {
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: `1px solid ${colors.muted}16`,
  },
  cycleWeakest: {
    fontSize: '13px',
    color: colors.yellow,
    fontFamily: font.family,
    textTransform: 'capitalize',
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
