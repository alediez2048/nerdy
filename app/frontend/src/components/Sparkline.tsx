// SVG sparkline — tiny inline quality trend chart
import { colors } from '../design/tokens'

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
}

export default function Sparkline({
  data,
  width = 80,
  height = 24,
}: SparklineProps) {
  if (data.length < 2) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1)) * width
    const y = height - ((val - min) / range) * (height - 4) - 2
    return `${x},${y}`
  })

  // Color: improving (last > first) = cyan, regressing = red
  const improving = data[data.length - 1] >= data[0]
  const color = improving ? colors.cyan : colors.red

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(' ')}
      />
    </svg>
  )
}
