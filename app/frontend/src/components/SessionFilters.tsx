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

  return (
    <div style={s.bar}>
      {FILTER_OPTIONS.map(({ key, label, options }) => (
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
      {hasFilters && (
        <button
          onClick={() => onChange({ audience: '', campaign_goal: '', status: '' })}
          style={s.clear}
        >
          Clear
        </button>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    gap: '16px',
    alignItems: 'flex-end',
    flexWrap: 'wrap',
    marginBottom: '20px',
  },
  group: { display: 'flex', flexDirection: 'column', gap: '4px' },
  label: { fontSize: '12px', color: colors.muted, fontFamily: font.family },
  select: {
    padding: '6px 12px',
    borderRadius: radii.input,
    border: `1px solid ${colors.muted}40`,
    background: colors.surface,
    color: colors.white,
    fontSize: '13px',
    fontFamily: font.family,
  },
  clear: {
    padding: '6px 14px',
    borderRadius: radii.button,
    border: `1px solid ${colors.muted}40`,
    background: 'transparent',
    color: colors.muted,
    cursor: 'pointer',
    fontSize: '12px',
    fontFamily: font.family,
  },
}
