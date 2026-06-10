type ScientificSpectrum = {
  x_axis: number[]
  y_axis: number[]
  x_unit: string
  y_unit: string
}

export function ScientificSpectrumPlot({
  spectrum,
  title,
  reverseX = false,
}: {
  spectrum?: ScientificSpectrum | null
  title: string
  reverseX?: boolean
}) {
  if (!spectrum?.x_axis.length) {
    return <div className="flex h-64 items-center justify-center text-sm text-slate-500">Рассчитанный спектр пока отсутствует.</div>
  }

  const width = 900
  const height = 260
  const padding = 32
  const minX = Math.min(...spectrum.x_axis)
  const maxX = Math.max(...spectrum.x_axis)
  const minY = Math.min(...spectrum.y_axis)
  const maxY = Math.max(...spectrum.y_axis)
  const xScale = (value: number) => {
    const fraction = (value - minX) / (maxX - minX || 1)
    return padding + (reverseX ? 1 - fraction : fraction) * (width - 2 * padding)
  }
  const yScale = (value: number) => height - padding - ((value - minY) / (maxY - minY || 1)) * (height - 2 * padding)
  const path = spectrum.x_axis
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${xScale(value).toFixed(2)} ${yScale(spectrum.y_axis[index]).toFixed(2)}`)
    .join(' ')

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full rounded-lg border border-slate-800 bg-slate-950">
      <path d={path} fill="none" stroke="#22d3ee" strokeWidth="1.8" />
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#334155" />
      <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#334155" />
      <text x={padding} y={18} fontSize="12" fill="#cbd5e1">{title}</text>
      <text x={width - padding} y={height - 8} textAnchor="end" fontSize="11" fill="#94a3b8">{spectrum.x_unit}</text>
      <text x={padding + 4} y={padding + 12} fontSize="10" fill="#94a3b8">{spectrum.y_unit}</text>
      <text x={padding} y={height - 8} fontSize="10" fill="#94a3b8">{reverseX ? maxX.toFixed(0) : minX.toFixed(0)}</text>
      <text x={width - padding} y={height - 8} textAnchor="end" fontSize="10" fill="#94a3b8">{reverseX ? minX.toFixed(0) : maxX.toFixed(0)}</text>
    </svg>
  )
}
