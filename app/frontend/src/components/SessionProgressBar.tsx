// Session progress bar — inline banner for running sessions in SessionDetail
// Uses polling on the REST API for reliable progress + SSE for real-time updates
import { useEffect, useRef, useState, useCallback } from 'react'
import { colors, font, radii } from '../design/tokens'
import { getSession } from '../api/sessions'
import type { ProgressSummary } from '../types/session'

interface Props {
  sessionId: string
  adCount: number
  initialProgress?: ProgressSummary | null
  onComplete?: () => void
}

const POLL_INTERVAL_MS = 3000

function formatEta(seconds: number): string {
  if (seconds < 60) return '< 1 min'
  const mins = Math.ceil(seconds / 60)
  if (mins === 1) return '~1 min'
  return `~${mins} min`
}

export default function SessionProgressBar({ sessionId, adCount, initialProgress, onComplete }: Props) {
  const [progress, setProgress] = useState<ProgressSummary | null>(initialProgress || null)
  const [status, setStatus] = useState<string>('pending')
  const [eta, setEta] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(Date.now())


  // Poll session endpoint for progress updates
  const pollProgress = useCallback(async () => {
    try {
      const session = await getSession(sessionId)
      setStatus(session.status)

      if (session.progress_summary) {
        setProgress(session.progress_summary)
      }

      // Stop polling on terminal states
      if (session.status === 'completed' || session.status === 'failed') {
        if (pollRef.current) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
        if (session.status === 'completed' && onComplete) {
          onComplete()
        }
      }
    } catch {
      // Silently ignore poll errors
    }
  }, [sessionId, onComplete])

  // Start polling
  useEffect(() => {
    // Initial poll immediately
    pollProgress()

    pollRef.current = setInterval(pollProgress, POLL_INTERVAL_MS)

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [pollProgress])

  // ETA calculation based on elapsed time and progress
  useEffect(() => {
    if (!progress) return
    const generated = progress.ads_generated || 0
    const target = progress.ad_count || adCount

    if (status === 'completed' || status === 'failed' || generated >= target) {
      setEta(null)
      return
    }

    if (generated > 0) {
      const elapsed = (Date.now() - startTimeRef.current) / 1000
      const timePerAd = elapsed / generated
      const remaining = target - generated
      setEta(formatEta(timePerAd * remaining))
    }
  }, [progress, status, adCount])

  const generated = progress?.ads_generated || 0
  const published = progress?.ads_published || 0
  const avgScore = progress?.current_score_avg || 0
  const cost = progress?.cost_so_far || 0
  const target = progress?.ad_count || adCount
  const batch = progress?.batch || 0
  const numBatches = progress?.num_batches || 0
  const cycle = progress?.current_cycle || 1

  // Progress percentage based on ads generated (fine-grained)
  const pct = target > 0
    ? Math.min((generated / target) * 100, 100)
    : 0

  // Stage label — adapts for video sessions
  const progressAny = progress as unknown as Record<string, unknown> | null
  const progressType = (progressAny?.type as string) || ''
  const isVideoProgress = progressType.startsWith('video_')

  let stageLabel = 'Starting pipeline...'
  if (status === 'completed') {
    stageLabel = 'Complete'
  } else if (status === 'failed') {
    stageLabel = 'Failed'
  } else if (isVideoProgress) {
    const vidAds = (progressAny?.videos_generated as number) || 0
    const vidVariants = (progressAny?.video_variants_generated as number) || 0
    const vidSelected = (progressAny?.videos_selected as number) || 0
    if (progressType === 'video_generating') {
      stageLabel = `Generating video ${progressAny?.ad_index || ''}...`
    } else if (progressType === 'video_evaluating') {
      stageLabel = `Evaluating video ${progressAny?.ad_index || ''}...`
    } else if (progressType === 'video_pipeline_complete') {
      stageLabel = `Complete — ${vidSelected} selected (${vidAds} ads, ${vidVariants} Fal jobs)`
    } else {
      stageLabel = `Video ads: ${vidAds} · Fal jobs: ${vidVariants} · Selected: ${vidSelected}`
    }
  } else if (generated > 0 && numBatches > 0) {
    stageLabel = `Cycle ${cycle} — Batch ${batch}/${numBatches} — ${generated} ads generated`
  } else if (generated > 0) {
    stageLabel = `Generating — ${generated} ads so far`
  } else if (status === 'running') {
    stageLabel = 'Generating ads...'
  }

  if (status === 'completed') {
    return (
      <div style={{ ...s.container, borderColor: `${colors.mint}40` }}>
        <div style={s.completeRow}>
          <span style={{ color: colors.mint, fontWeight: 600, fontSize: '14px' }}>
            Pipeline complete
          </span>
          <span style={{ color: colors.muted, fontSize: '12px' }}>
            {published} ads published · avg {avgScore.toFixed(1)} · ${cost.toFixed(2)}
          </span>
        </div>
        <div style={s.barBg}>
          <div style={{ ...s.barFill, width: '100%', background: colors.mint }} />
        </div>
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div style={{ ...s.container, borderColor: `${colors.red}40` }}>
        <div style={s.topRow}>
          <span style={{ color: colors.red, fontWeight: 600, fontSize: '14px' }}>
            Pipeline failed
          </span>
        </div>
        <div style={s.barBg}>
          <div style={{ ...s.barFill, width: `${pct}%`, background: colors.red }} />
        </div>
      </div>
    )
  }

  return (
    <div style={s.container}>
      {/* Top row: stage label + ETA */}
      <div style={s.topRow}>
        <div style={s.stageRow}>
          <span style={{ ...s.dot, background: status === 'running' ? colors.mint : colors.yellow }} />
          <span style={s.stageLabel}>{stageLabel}</span>
        </div>
        {eta && (
          <span style={s.eta}>{eta} remaining</span>
        )}
      </div>

      {/* Progress bar */}
      <div style={s.barBg}>
        <div style={{ ...s.barFill, width: `${Math.max(pct, status === 'running' ? 2 : 0)}%` }}>
          <div style={s.barShimmer} />
        </div>
      </div>

      {/* Stats row */}
      <div style={s.statsRow}>
        <Stat label="Generated" value={`${generated}/${target}`} />
        <Stat label="Published" value={`${published}`} color={colors.mint} />
        <Stat label="Avg Score" value={avgScore > 0 ? avgScore.toFixed(1) : '—'} />
        <Stat label="Cost" value={`$${cost.toFixed(2)}`} color={colors.yellow} />
      </div>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={s.stat}>
      <div style={{ ...s.statValue, color: color || colors.white }}>{value}</div>
      <div style={s.statLabel}>{label}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  container: {
    background: colors.surface,
    borderRadius: radii.input,
    border: `1px solid ${colors.cyan}30`,
    padding: '16px 18px',
    marginBottom: '20px',
    fontFamily: font.family,
  },
  topRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  completeRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px',
  },
  stageRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  dot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  stageLabel: {
    color: colors.white,
    fontSize: '13px',
    fontWeight: 600,
  },
  eta: {
    color: colors.cyan,
    fontSize: '12px',
    fontWeight: 500,
  },
  barBg: {
    height: '8px',
    background: `${colors.muted}20`,
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '12px',
  },
  barFill: {
    height: '100%',
    borderRadius: '4px',
    background: `linear-gradient(90deg, ${colors.cyan}, ${colors.mint})`,
    transition: 'width 0.6s ease',
    position: 'relative',
    overflow: 'hidden',
  },
  barShimmer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent)',
    animation: 'shimmer 2s infinite',
  },
  statsRow: {
    display: 'flex',
    gap: '16px',
    justifyContent: 'space-between',
  },
  stat: {
    textAlign: 'center',
    flex: 1,
  },
  statValue: {
    fontSize: '15px',
    fontWeight: 600,
    color: colors.white,
  },
  statLabel: {
    fontSize: '11px',
    color: colors.muted,
    marginTop: '2px',
  },
}
