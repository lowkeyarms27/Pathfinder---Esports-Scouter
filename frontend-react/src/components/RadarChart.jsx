import { RADAR_DIMS } from '../lib/constants'

function polarToXY(angle, r, cx, cy) {
  const rad = (angle - 90) * (Math.PI / 180)
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  }
}

function polyPoints(values, maxR, cx, cy, dims) {
  return dims.map((d, i) => {
    const angle = (360 / dims.length) * i
    const r     = (values[d.key] ?? 0.5) * maxR
    const p     = polarToXY(angle, r, cx, cy)
    return `${p.x},${p.y}`
  }).join(' ')
}

export default function RadarChart({ vector = {}, proVector = null, size = 300 }) {
  const cx   = size / 2
  const cy   = size / 2
  const maxR = size / 2 - 36
  const dims = RADAR_DIMS
  const rings = [0.25, 0.5, 0.75, 1.0]

  return (
    <svg width={size} height={size} className="overflow-visible">
      {/* Grid rings */}
      {rings.map(r => (
        <polygon key={r}
          points={dims.map((_, i) => {
            const p = polarToXY((360 / dims.length) * i, r * maxR, cx, cy)
            return `${p.x},${p.y}`
          }).join(' ')}
          fill="none" stroke="rgba(100,116,139,0.2)" strokeWidth="1"
        />
      ))}

      {/* Axis lines */}
      {dims.map((_, i) => {
        const outer = polarToXY((360 / dims.length) * i, maxR, cx, cy)
        return <line key={i} x1={cx} y1={cy} x2={outer.x} y2={outer.y}
          stroke="rgba(100,116,139,0.15)" strokeWidth="1" />
      })}

      {/* Pro vector (ghost) */}
      {proVector && (
        <polygon
          points={polyPoints(proVector, maxR, cx, cy, dims)}
          fill="rgba(148,163,184,0.08)"
          stroke="rgba(148,163,184,0.3)"
          strokeWidth="1.5"
          strokeDasharray="4 3"
        />
      )}

      {/* Player vector */}
      <polygon
        points={polyPoints(vector, maxR, cx, cy, dims)}
        fill="rgba(0,255,136,0.1)"
        stroke="rgba(0,255,136,0.8)"
        strokeWidth="2"
      />

      {/* Dots on player vector */}
      {dims.map((d, i) => {
        const angle = (360 / dims.length) * i
        const r     = (vector[d.key] ?? 0.5) * maxR
        const p     = polarToXY(angle, r, cx, cy)
        return <circle key={i} cx={p.x} cy={p.y} r="3.5"
          fill="#00ff88" stroke="#080808" strokeWidth="1.5" />
      })}

      {/* Labels */}
      {dims.map((d, i) => {
        const angle  = (360 / dims.length) * i
        const labelR = maxR + 18
        const p      = polarToXY(angle, labelR, cx, cy)
        const anchor = p.x < cx - 4 ? 'end' : p.x > cx + 4 ? 'start' : 'middle'
        return (
          <text key={i} x={p.x} y={p.y + 4} textAnchor={anchor}
            className="fill-slate-500 text-[8px] font-semibold uppercase tracking-wide"
            style={{ fontSize: '8px', fontFamily: 'inherit' }}>
            {d.label}
          </text>
        )
      })}
    </svg>
  )
}
