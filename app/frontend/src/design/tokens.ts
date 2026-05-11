// Design system tokens

export const colors = {
  ink: '#0a0a0f',
  surface: '#12121a',
  cyan: '#00f0ff',
  mint: '#ff2d95',
  lightPurple: '#b44dff',
  yellow: '#ffe44d',
  red: '#ff3355',
  white: '#f0f0f5',
  muted: '#6b7280',
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
