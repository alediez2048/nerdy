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

export default function SessionCard({
  session,
  onDelete,
}: {
  session: SessionSummary
  onDelete?: (id: string) => void
}) {
  const navigate = useNavigate()
  const config = session.config || {}
  const results = session.results_summary || null
  const preview = session.ad_preview || null
  const isRunning = session.status === 'running'
  const progress = session.progress_summary

  const audience = (config.audience as string) || ''
  const goal = (config.campaign_goal as string) || ''
  const adCount = (config.ad_count as number) || 0

  return (
    <div
      onClick={() => navigate(`/sessions/${session.session_id}`)}
      style={s.card}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${colors.cyan}40`)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'transparent')}
    >
      <div style={s.header}>
        <div style={s.headerMain}>
          <div style={s.titleRow}>
            <span style={s.name}>{session.name || session.session_id}</span>
          </div>
          <div style={s.metaRow}>
            <StatusBadge status={session.status} />
            <span style={s.date}>{relativeTime(session.created_at)}</span>
          </div>
        </div>
      </div>

      <div style={s.badges}>
        {audience && <Badge label={audience.charAt(0).toUpperCase() + audience.slice(1)} color={colors.cyan} />}
        {goal && <Badge label={goal.charAt(0).toUpperCase() + goal.slice(1)} color={colors.mint} />}
        {adCount > 0 && <Badge label={`${adCount} ads`} color={colors.muted} />}
        {typeof config.persona === 'string' && config.persona !== 'auto' && (
          <Badge label={String(config.persona).replace(/_/g, ' ')} color={colors.lightPurple} />
        )}
      </div>

      {preview ? (
        <div style={s.previewPanel}>
          <div style={s.metricIntro}>First ad preview</div>
          {preview.image_url ? (
            <img
              src={`/api${preview.image_url}`}
              alt={preview.headline || preview.ad_id}
              style={s.previewImage}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
            />
          ) : (
            <div style={s.previewPlaceholder}>No image available yet</div>
          )}
          <div style={s.previewCopy}>
            <div style={s.previewHeadline}>
              {preview.headline || `Ad ${preview.ad_id}`}
            </div>
            <div style={s.previewText}>
              {preview.primary_text || 'Preview copy will appear here once the first ad is generated.'}
            </div>
            <div style={s.previewMeta}>
              <span>{preview.status.replace(/_/g, ' ')}</span>
              <span>{preview.aggregate_score ? `${preview.aggregate_score.toFixed(1)} score` : 'Not scored yet'}</span>
            </div>
          </div>
        </div>
      ) : isRunning && progress ? (
        <div style={s.metricPanel}>
          <div style={s.metricIntro}>Live progress</div>
          <div style={s.metricGrid}>
            <Metric label="Cycle" value={`${progress.current_cycle}`} />
            <Metric label="Generated" value={`${progress.ads_generated}`} />
            <Metric label="Avg Score" value={progress.current_score_avg.toFixed(1)} />
            <Metric label="Cost" value={`$${progress.cost_so_far.toFixed(2)}`} />
          </div>
        </div>
      ) : results ? (
        <div style={s.metricPanel}>
          <div style={s.metricIntro}>Session performance</div>
          <div style={s.metricGrid}>
            <div style={s.metricBox}>
              <div style={s.metricValue}>
                {`${results.ads_published || 0}/${results.ads_generated || adCount}`}
              </div>
              <div style={s.metricLabel}>Published</div>
              <div style={s.metricSubvalue}>
                Session Cost ${((results.cost_so_far as number) || 0).toFixed(2)}
              </div>
            </div>
            <Metric label="Avg Score" value={((results.avg_score as number) || 0).toFixed(1)} />
            <div style={s.sparklineWrap}>
              <div style={s.sparklineLabel}>Quality Trend</div>
              <Sparkline data={[6.5, 7.0, 7.3, 7.6, 7.8]} />
            </div>
          </div>
        </div>
      ) : (
        <div style={s.metricPanel}>
          <div style={s.metricIntro}>Session status</div>
          <span style={s.emptyMessage}>
            {session.status === 'pending' ? 'Waiting to start...' : 'No results yet'}
          </span>
        </div>
      )}

      <div style={s.actions}>
        <button
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/sessions/${session.session_id}`)
          }}
          style={s.openBtn}
        >
          Open Session
        </button>
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              if (window.confirm(`Delete session "${session.name || session.session_id}"?`)) {
                onDelete(session.session_id)
              }
            }}
            style={s.deleteBtn}
          >
            Delete
          </button>
        )}
      </div>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={s.metricBox}>
      <div style={s.metricValue}>{value}</div>
      <div style={s.metricLabel}>{label}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '18px 18px 16px',
    cursor: 'pointer',
    border: '1px solid transparent',
    transition: 'border-color 0.2s',
    fontFamily: font.family,
    minHeight: '330px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  header: {
    display: 'flex',
    marginBottom: '12px',
  },
  headerMain: { display: 'flex', flexDirection: 'column', gap: '6px', minWidth: 0, flex: 1 },
  titleRow: { display: 'flex', alignItems: 'center', minWidth: 0, width: '100%' },
  name: {
    fontSize: '18px',
    fontWeight: 600,
    color: colors.white,
    lineHeight: 1.3,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    minWidth: 0,
    flex: 1,
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '10px',
    flexWrap: 'wrap',
  },
  date: { fontSize: '12px', color: colors.muted, whiteSpace: 'nowrap' },
  badges: { display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' },
  metricPanel: {
    background: `${colors.ink}26`,
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}18`,
    padding: '14px',
    minHeight: '132px',
  },
  previewPanel: {
    background: `${colors.ink}26`,
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}18`,
    padding: '14px',
    minHeight: '132px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  metricIntro: {
    fontSize: '12px',
    color: colors.muted,
    marginBottom: '10px',
  },
  previewImage: {
    width: '100%',
    maxHeight: '180px',
    objectFit: 'contain',
    borderRadius: radii.input,
    background: `${colors.surface}80`,
  },
  previewPlaceholder: {
    minHeight: '120px',
    borderRadius: radii.input,
    background: `${colors.surface}80`,
    color: colors.muted,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '12px',
    textAlign: 'center',
    padding: '12px',
  },
  previewCopy: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  previewHeadline: {
    fontSize: '13px',
    fontWeight: 600,
    color: colors.white,
    lineHeight: 1.4,
  },
  previewText: {
    fontSize: '12px',
    color: colors.muted,
    lineHeight: 1.5,
    display: '-webkit-box',
    WebkitLineClamp: 3,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  previewMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    fontSize: '11px',
    color: colors.muted,
    textTransform: 'capitalize',
  },
  metricGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
    gap: '10px',
    alignItems: 'stretch',
  },
  metricBox: {
    background: `${colors.surface}80`,
    borderRadius: radii.input,
    padding: '10px',
    minHeight: '64px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  },
  metricValue: {
    fontSize: '16px',
    fontWeight: 600,
    color: colors.white,
  },
  metricLabel: {
    fontSize: '11px',
    color: colors.muted,
    marginTop: '4px',
  },
  metricSubvalue: {
    fontSize: '11px',
    color: colors.cyan,
    marginTop: '8px',
  },
  sparklineWrap: {
    background: `${colors.surface}80`,
    borderRadius: radii.input,
    padding: '10px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    minHeight: '64px',
  },
  sparklineLabel: {
    fontSize: '11px',
    color: colors.muted,
    marginBottom: '6px',
  },
  emptyMessage: {
    color: colors.muted,
    fontSize: '13px',
    display: 'block',
  },
  actions: {
    display: 'flex',
    gap: '8px',
    marginTop: '14px',
    flexWrap: 'wrap',
  },
  openBtn: {
    padding: '8px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}50`,
    background: `${colors.cyan}14`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
  deleteBtn: {
    padding: '8px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.red}40`,
    background: 'transparent',
    color: colors.red,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
}
