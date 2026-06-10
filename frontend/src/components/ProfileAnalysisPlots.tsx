type Spectrum = {
  x_axis: number[]
  y_axis: number[]
  x_unit: string
  y_unit: string
}

export function MassSpectrumPlot({
  spectrum,
  fragments,
}: {
  spectrum?: Spectrum | null
  fragments?: Array<{ mz: number; intensity: number; formula: string; origin: string }>
}) {
  if (!spectrum?.x_axis.length) return <Empty text="Фрагментационный спектр отсутствует." />
  const width = 900
  const height = 300
  const padding = 34
  const maxX = Math.max(...spectrum.x_axis)
  const xScale = (value: number) => padding + (value / maxX) * (width - 2 * padding)
  const yScale = (value: number) => height - padding - (value / 100) * (height - 2 * padding)
  return (
    <div className="space-y-3">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-72 w-full rounded-lg border border-slate-800 bg-slate-950">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#475569" />
        {(fragments ?? []).map(fragment => (
          <g key={`${fragment.mz}-${fragment.formula}`}>
            <line x1={xScale(fragment.mz)} x2={xScale(fragment.mz)} y1={height - padding} y2={yScale(fragment.intensity)} stroke="#22d3ee" strokeWidth="2" />
            {fragment.intensity >= 45 && <text x={xScale(fragment.mz)} y={yScale(fragment.intensity) - 6} textAnchor="middle" fill="#cbd5e1" fontSize="10">{fragment.mz.toFixed(1)}</text>}
          </g>
        ))}
        <text x={width - padding} y={height - 8} textAnchor="end" fill="#94a3b8" fontSize="11">m/z</text>
        <text x={padding} y={18} fill="#94a3b8" fontSize="11">Относительная интенсивность, %</text>
      </svg>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {(fragments ?? []).slice().sort((a, b) => b.intensity - a.intensity).slice(0, 9).map(fragment => (
          <div key={`${fragment.origin}-${fragment.mz}`} className="rounded border border-slate-800 p-2 text-xs text-slate-300">
            <b>m/z {fragment.mz.toFixed(3)}</b> · {fragment.intensity.toFixed(1)}%<br />
            {fragment.formula} · {fragment.origin}
          </div>
        ))}
      </div>
    </div>
  )
}

export function EnsemblePopulationPlot({
  conformers,
}: {
  conformers?: Array<{ id: number; relative_energy_kcal_mol: number; boltzmann_weight: number }>
}) {
  if (!conformers?.length) return <Empty text="Ансамбль конформеров отсутствует." />
  return (
    <div className="space-y-2">
      {conformers.slice(0, 16).map(conformer => (
        <div key={conformer.id} className="grid grid-cols-[64px_1fr_120px] items-center gap-3 text-xs">
          <div>Конф. {conformer.id}</div>
          <div className="h-5 overflow-hidden rounded bg-slate-900">
            <div className="h-full bg-cyan-500" style={{ width: `${Math.max(1, conformer.boltzmann_weight * 100)}%` }} />
          </div>
          <div className="text-right text-slate-400">{(conformer.boltzmann_weight * 100).toFixed(2)}% · ΔE {conformer.relative_energy_kcal_mol.toFixed(2)}</div>
        </div>
      ))}
    </div>
  )
}

export function PeriodicCellPlot({
  vectors,
  atomCount,
}: {
  vectors?: number[][]
  atomCount?: number
}) {
  if (!vectors?.length) return <Empty text="Периодическая ячейка отсутствует." />
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <svg viewBox="0 0 420 300" className="h-72 w-full rounded-lg border border-slate-800 bg-slate-950">
        <path d="M90 220 L285 220 L350 160 L155 160 Z M90 220 L90 70 L285 70 L285 220 M285 70 L350 10 L350 160 M90 70 L155 10 L350 10 M155 10 L155 160" fill="none" stroke="#22d3ee" strokeWidth="2" />
        <text x="22" y="28" fill="#94a3b8" fontSize="12">Суперъячейка 2×2×1</text>
        <circle cx="155" cy="160" r="9" fill="#f59e0b" />
        <circle cx="285" cy="220" r="9" fill="#60a5fa" />
        <circle cx="220" cy="115" r="9" fill="#f87171" />
      </svg>
      <div className="space-y-3 text-sm text-slate-300">
        <div>Число атомов в отображаемой суперъячейке: {atomCount ?? '—'}</div>
        {vectors.map((vector, index) => (
          <div key={index} className="rounded border border-slate-800 p-3">a{index + 1} = [{vector.map(value => value.toFixed(2)).join(', ')}] Å</div>
        ))}
      </div>
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return <div className="flex h-60 items-center justify-center text-sm text-slate-500">{text}</div>
}
