// Session list filter bar
import { colors, radii, font } from '../design/tokens'

export interface Filters {
  audience: string
  campaign_goal: string
  status: string
}

interface Props {
  filters: Filters
  onChange: (filters: Filters) => void
}

const FILTER_OPTIONS: { key: keyof Filters; label: string; options: string[] }[] = [
  { key: 'audience', label: 'Audience', options: ['', 'parents', 'students'] },
  { key: 'campaign_goal', label: 'Goal', options: ['', 'awareness', 'conversion'] },
  { key: 'status', label: 'Status', options: ['', 'pending', 'running', 'completed', 'failed'] },
]

export default function SessionFilters({ filters, onChange }: Props) {
  const hasFilters = filters.audience || filters.campaign_goal || filters.status
  const statusOptions = ['', 'pending', 'running', 'completed', 'failed']

  return (
    <div style={s.bar}>
      <div style={s.topRow}>
        <div>
          <div style={s.heading}>Filter Sessions</div>
          <div style={s.subheading}>
            Narrow the dashboard by lifecycle, audience, and campaign goal.
          </div>
        </div>
        {hasFilters && (
          <button
            onClick={() => onChange({ audience: '', campaign_goal: '', status: '' })}
            style={s.clear}
          >
            Clear all
          </button>
        )}
      </div>

      <div style={s.statusRow}>
        {statusOptions.map((status) => (
          <button
            key={status || 'all'}
            onClick={() => onChange({ ...filters, status })}
            style={filters.status === status ? s.chipActive : s.chip}
          >
            {status ? status.replace(/_/g, ' ') : 'all statuses'}
          </button>
        ))}
      </div>

      <div style={s.controlsRow}>
        {FILTER_OPTIONS.filter(({ key }) => key !== 'status').map(({ key, label, options }) => (
          <div key={key} style={s.group}>
            <label style={s.label}>{label}</label>
            <select
              value={filters[key]}
              onChange={(e) => onChange({ ...filters, [key]: e.target.value })}
              style={s.select}
            >
              <option value="">All</option>
              {options.filter(Boolean).map((opt) => (
                <option key={opt} value={opt}>
                  {opt.charAt(0).toUpperCase() + opt.slice(1)}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    marginBottom: '24px',
    padding: '18px 20px',
    background: colors.surface,
    borderRadius: radii.card,
    border: `1px solid ${colors.muted}18`,
  },
  topRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: '12px',
    flexWrap: 'wrap',
  },
  heading: {
    fontSize: '14px',
    fontWeight: 600,
    color: colors.white,
    fontFamily: font.family,
  },
  subheading: {
    fontSize: '12px',
    color: colors.muted,
    marginTop: '4px',
    fontFamily: font.family,
  },
  statusRow: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  controlsRow: {
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-end',
    flexWrap: 'wrap',
  },
  group: { display: 'flex', flexDirection: 'column', gap: '4px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
  select: {
    padding: '8px 12px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: colors.surface,
    color: colors.white,
    fontSize: '13px',
    fontFamily: font.family,
    minWidth: '150px',
  },
  clear: {
    padding: '8px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
  chip: {
    padding: '8px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}30`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    textTransform: 'capitalize',
    fontFamily: font.family,
  },
  chipActive: {
    padding: '8px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.cyan}`,
    background: `${colors.cyan}18`,
    color: colors.cyan,
    cursor: 'pointer',
    fontSize: '12px',
    textTransform: 'capitalize',
    fontFamily: font.family,
  },
}
