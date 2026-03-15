// Reusable badge component
import { colors, radii, font } from '../design/tokens'

interface BadgeProps {
  label: string
  color?: string
  bg?: string
}

export default function Badge({ label, color = colors.cyan, bg }: BadgeProps) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '3px 12px',
        borderRadius: radii.button,
        border: `1px solid ${color}60`,
        background: bg || `${color}15`,
        color,
        fontSize: '12px',
        fontWeight: 600,
        fontFamily: font.family,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}

const STATUS_COLORS: Record<string, string> = {
  pending: colors.yellow,
  running: colors.cyan,
  completed: colors.mint,
  failed: colors.red,
}

export function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || colors.muted
  return <Badge label={status} color={color} />
}
