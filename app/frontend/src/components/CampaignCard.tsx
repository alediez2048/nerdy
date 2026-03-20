// Campaign card — one card per campaign in the list
import { useNavigate } from 'react-router-dom'
import { colors, radii, font } from '../design/tokens'
import Badge, { StatusBadge } from './Badge'
import type { CampaignSummary } from '../types/campaign'
import { updateCampaign } from '../api/campaigns'

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

export default function CampaignCard({
  campaign,
  onArchive,
}: {
  campaign: CampaignSummary
  onArchive?: (id: string) => void
}) {
  const navigate = useNavigate()

  const handleArchive = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (window.confirm(`Archive campaign "${campaign.name}"?`)) {
      try {
        await updateCampaign(campaign.campaign_id, { status: 'archived' })
        onArchive?.(campaign.campaign_id)
      } catch (err) {
        alert(err instanceof Error ? err.message : 'Failed to archive campaign')
      }
    }
  }

  return (
    <div
      onClick={() => navigate(`/campaigns/${campaign.campaign_id}`)}
      style={s.card}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${colors.cyan}40`)}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'transparent')}
    >
      <div style={s.header}>
        <div style={s.headerMain}>
          <div style={s.titleRow}>
            <span style={s.name}>{campaign.name}</span>
          </div>
          <div style={s.metaRow}>
            <StatusBadge status={campaign.status} />
            <span style={s.date}>{relativeTime(campaign.created_at)}</span>
          </div>
        </div>
      </div>

      {campaign.description && (
        <p style={s.description}>
          {campaign.description.length > 120
            ? `${campaign.description.substring(0, 120)}...`
            : campaign.description}
        </p>
      )}

      <div style={s.badges}>
        {campaign.audience && (
          <Badge
            label={campaign.audience.charAt(0).toUpperCase() + campaign.audience.slice(1)}
            color={colors.cyan}
          />
        )}
        {campaign.campaign_goal && (
          <Badge
            label={campaign.campaign_goal.charAt(0).toUpperCase() + campaign.campaign_goal.slice(1)}
            color={colors.mint}
          />
        )}
        <Badge
          label={`${campaign.session_count} ${campaign.session_count === 1 ? 'session' : 'sessions'}`}
          color={colors.muted}
        />
      </div>

      <div style={s.actions}>
        <button
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/campaigns/${campaign.campaign_id}`)
          }}
          style={s.openBtn}
        >
          Open Campaign
        </button>
        {campaign.status === 'active' && onArchive && (
          <button onClick={handleArchive} style={s.archiveBtn}>
            Archive
          </button>
        )}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: {
    background: colors.surface,
    borderRadius: radii.card,
    padding: '18px 18px 16px',
    cursor: 'pointer',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: 'transparent',
    transition: 'border-color 0.2s',
    fontFamily: font.family,
    minHeight: '200px',
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
  description: {
    fontSize: '13px',
    color: colors.muted,
    lineHeight: 1.5,
    marginBottom: '12px',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  },
  badges: { display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' },
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
  archiveBtn: {
    padding: '8px 16px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: font.family,
  },
}
