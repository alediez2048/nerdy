// Ad-Ops-Autopilot — Design system tokens (PRD Section 4.7.10)

export const colors = {
  ink: '#202344',
  surface: '#161c2c',
  cyan: '#17e2ea',
  mint: '#35dd8b',
  lightPurple: '#a488f7',
  yellow: '#ffcb19',
  red: '#ff4e00',
  white: '#ffffff',
  muted: '#8b92a5',
} as const

export const gradients = {
  hero: `linear-gradient(135deg, ${colors.cyan}, ${colors.mint})`,
  card: `linear-gradient(135deg, ${colors.surface}, ${colors.ink})`,
} as const

export const radii = {
  card: '24px',
  button: '100px',
  input: '12px',
} as const

export const font = {
  family: "'Poppins', sans-serif",
} as const
