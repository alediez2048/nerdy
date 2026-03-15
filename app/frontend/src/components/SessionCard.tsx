// Session card — one card per session in the list
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import Badge, { StatusBadge } from './Badge'
import Sparkline from './Sparkline'
import type { SessionSummary } from '../types/session'

function relativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function SessionCard({ session }: { session: SessionSummary }) {
  const navigate = useNavigate()
  const config = session.config || {}
  const results = (session as unknown as Record<string, unknown>).results_summary as Record<string, unknown> | null
  const isRunning = session.status === 'running'
  const progress = session.progress_summary

  const audience = (config.audience as string) || ''
  const goal = (config.campaign_goal as string) || ''
  const adCount = (config.ad_count as number) || 0

  return (
    <div
      onClick={() =>
        navigate(isRunning ? `/sessions/${session.session_id}/live` : `/sessions/${session.session_id}`)
      }
      style={s.card}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${colors.cyan}40`)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'transparent')}
    >
      {/* Header */}
      <div style={s.header}>
        <div style={s.titleRow}>
          <span style={s.name}>{session.name || session.session_id}</span>
          <StatusBadge status={session.status} />
        </div>
        <span style={s.date}>{relativeTime(session.created_at)}</span>
      </div>

      {/* Badges */}
      <div style={s.badges}>
        {audience && <Badge label={audience.charAt(0).toUpperCase() + audience.slice(1)} color={colors.cyan} />}
        {goal && <Badge label={goal.charAt(0).toUpperCase() + goal.slice(1)} color={colors.mint} />}
        {adCount > 0 && <Badge label={`${adCount} ads`} color={colors.muted} />}
      </div>

      {/* Metrics or Progress */}
      {isRunning && progress ? (
        <div style={s.metrics}>
          <Metric label="Cycle" value={`${progress.current_cycle}`} />
          <Metric label="Generated" value={`${progress.ads_generated}`} />
          <Metric label="Avg Score" value={progress.current_score_avg.toFixed(1)} />
          <Metric label="Cost" value={`$${progress.cost_so_far.toFixed(2)}`} />
        </div>
      ) : results ? (
        <div style={s.metrics}>
          <Metric
            label="Published"
            value={`${results.ads_published || 0}/${results.ads_generated || adCount}`}
          />
          <Metric label="Avg Score" value={((results.avg_score as number) || 0).toFixed(1)} />
          <Metric
            label="Cost/Ad"
            value={`$${((results.cost_so_far as number) || 0).toFixed(2)}`}
          />
          <Sparkline data={[6.5, 7.0, 7.3, 7.6, 7.8]} />
        </div>
      ) : (
        <div style={s.metrics}>
          <span style={{ color: colors.muted, fontSize: '13px' }}>
            {session.status === 'pending' ? 'Waiting to start...' : 'No results yet'}
          </span>
        </div>
      )}

      {/* Watch Live button for running */}
      {isRunning && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/sessions/${session.session_id}/live`)
          }}
          style={s.watchLive}
        >
          Watch Live →
        </button>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '16px', fontWeight: 600, color: colors.white }}>{value}</div>
      <div style={{ fontSize: '11px', color: colors.muted }}>{label}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '20px 24px',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'border-color 0.2s',
    fontFamily: font.family,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  titleRow: { display: 'flex', alignItems: 'center', gap: '10px' },
  name: { fontSize: '16px', fontWeight: 600, color: colors.white },
  date: { fontSize: '12px', color: colors.muted, whiteSpace: 'nowrap' },
  badges: { display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' },
  metrics: {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
  },
  watchLive: {
    marginTop: '12px',
    padding: '6px 16px',
    borderRadius: radii.button,
    border: 'none',
    background: `${colors.cyan}20`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
}
