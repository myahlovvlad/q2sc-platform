type Spectrum = {
  x_axis: number[]
  y_axis: number[]
  peaks?: Array<{ position: number; intensity: number; label?: string }>
}

export function SpectrumPlot({ spectrum }: { spectrum?: Spectrum | null }) {
  if (!spectrum) {
    return <div className="flex h-72 items-center justify-center text-sm text-slate-500">Нет спектра для отображения</div>
  }

  const width = 900
  const height = 280
  const pad = 24
  const xs = spectrum.x_axis
  const ys = spectrum.y_axis
  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const xScale = (x: number) => pad + ((maxX - x) / (maxX - minX || 1)) * (width - 2 * pad)
  const yScale = (y: number) => height - pad - ((y - minY) / (maxY - minY || 1)) * (height - 2 * pad)
  const path = xs.map((x, index) => `${index === 0 ? 'M' : 'L'} ${xScale(x).toFixed(2)} ${yScale(ys[index]).toFixed(2)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-72 w-full rounded-lg border border-slate-800 bg-slate-950">
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.8" className="text-cyan-300" />
      <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#334155" />
      <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#334155" />
      {[220, 180, 140, 100, 60, 20, 0].map(tick => (
        <g key={tick}>
          <line x1={xScale(tick)} x2={xScale(tick)} y1={height - pad} y2={height - pad + 4} stroke="#64748b" />
          <text x={xScale(tick)} y={height - 5} textAnchor="middle" fontSize="10" fill="#94a3b8">{tick}</text>
        </g>
      ))}
      {(spectrum.peaks ?? []).map((peak, index) => (
        <g key={`${peak.position}-${index}`}>
          <line x1={xScale(peak.position)} x2={xScale(peak.position)} y1={pad} y2={height - pad} stroke="#f59e0b" strokeDasharray="4 4" opacity="0.5" />
          <text x={xScale(peak.position)} y={pad + 14 + index * 12} textAnchor="middle" fontSize="10" fill="#fbbf24">{peak.label ?? peak.position.toFixed(1)}</text>
        </g>
      ))}
      <text x={width - pad} y={pad} textAnchor="end" fontSize="11" fill="#94a3b8">ЯМР 13C, ppm</text>
    </svg>
  )
}
