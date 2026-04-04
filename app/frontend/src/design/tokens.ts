// Design system tokens

export const colors = {
  ink: '#1a1a2e',
  surface: '#16213e',
  cyan: '#e2a517',
  mint: '#f0c040',
  lightPurple: '#c4956a',
  yellow: '#f0c040',
  red: '#e74c3c',
  white: '#ffffff',
  muted: '#94a3b8',
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
