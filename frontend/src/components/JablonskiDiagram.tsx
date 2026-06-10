type ExcitedState = {
  state: string
  energy_ev: number
  oscillator_strength: number
}

export function JablonskiDiagram({ states }: { states?: ExcitedState[] | null }) {
  if (!states?.length) {
    return <div className="flex h-64 items-center justify-center text-sm text-slate-500">Возбуждённые состояния ещё не рассчитаны.</div>
  }

  const width = 520
  const height = 300
  const padding = 36
  const maximum = Math.max(...states.map(state => state.energy_ev))
  const yScale = (energy: number) => height - padding - (energy / maximum) * (height - 2 * padding)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-64 w-full rounded-lg border border-slate-800 bg-slate-950">
      <line x1={100} x2={420} y1={height - padding} y2={height - padding} stroke="#e2e8f0" strokeWidth="3" />
      <text x={72} y={height - padding + 4} fill="#e2e8f0" fontSize="12">S0</text>
      {states.map((state, index) => {
        const y = yScale(state.energy_ev)
        const arrowX = 150 + (index % 6) * 42
        return (
          <g key={state.state}>
            <line x1={100} x2={420} y1={y} y2={y} stroke="#22d3ee" strokeWidth="2" />
            <text x={430} y={y + 4} fill="#67e8f9" fontSize="11">{state.state} {state.energy_ev.toFixed(2)} eV</text>
            <line x1={arrowX} x2={arrowX} y1={height - padding - 5} y2={y + 7} stroke="#f59e0b" strokeWidth={Math.max(1, state.oscillator_strength * 8)} />
            <polygon points={`${arrowX - 4},${y + 12} ${arrowX + 4},${y + 12} ${arrowX},${y + 4}`} fill="#f59e0b" />
          </g>
        )
      })}
      <text x={12} y={18} fill="#94a3b8" fontSize="11">Вертикальные синглетные переходы</text>
    </svg>
  )
}
