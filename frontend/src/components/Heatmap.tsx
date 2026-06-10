type ScreeningResponse = {
  ppm_axis: number[]
  intensity_matrix: number[][]
  rows: Array<{ name: string; status: string; match_score: number }>
}

function intensityToClass(value: number) {
  const normalized = Math.max(-2, Math.min(4, value))
  if (normalized > 3) return 'bg-cyan-200'
  if (normalized > 2) return 'bg-cyan-400'
  if (normalized > 1) return 'bg-blue-500'
  if (normalized > 0) return 'bg-slate-500'
  return 'bg-slate-900'
}

export function Heatmap({ data, onSelect }: { data?: ScreeningResponse | null; onSelect?: (index: number) => void }) {
  if (!data) {
    return <div className="flex h-72 items-center justify-center text-sm text-slate-500">Запустите пакетный скрининг</div>
  }

  const sampleStep = Math.max(1, Math.floor(data.ppm_axis.length / 90))
  return (
    <div className="overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-3">
      <div className="mb-3 grid grid-cols-[160px_1fr_70px] gap-3 text-xs text-slate-400">
        <div>Кандидат</div><div>Спектр как штрихкод, 220→0 ppm</div><div>Оценка</div>
      </div>
      <div className="space-y-2">
        {data.rows.map((row, rowIndex) => (
          <button key={`${row.name}-${rowIndex}`} onClick={() => onSelect?.(rowIndex)} className="grid w-full grid-cols-[160px_1fr_70px] items-center gap-3 rounded-md px-2 py-1 text-left hover:bg-slate-900">
            <div className="truncate text-xs text-slate-200">{row.name}</div>
            <div className="flex h-5 overflow-hidden rounded border border-slate-800">
              {(data.intensity_matrix[rowIndex] ?? [])
                .filter((_, index) => index % sampleStep === 0)
                .map((value, index) => <div key={index} className={`h-full flex-1 ${intensityToClass(value)}`} />)}
            </div>
            <div className="text-right text-xs text-slate-300">{row.status === 'SUCCESS' ? row.match_score.toFixed(1) : row.status}</div>
          </button>
        ))}
      </div>
    </div>
  )
}
