import { useMemo, useState } from 'react'
import {
  Activity,
  Atom,
  BrainCircuit,
  Box,
  Database,
  Download,
  FlaskConical,
  GitBranch,
  HelpCircle,
  Loader2,
  Network,
  Search,
} from 'lucide-react'
import { Badge } from './components/ui/badge'
import { Button } from './components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Input } from './components/ui/input'
import { SpectrumPlot } from './components/SpectrumPlot'
import { Heatmap } from './components/Heatmap'
import { MoleculeViewer } from './components/MoleculeViewer'
import { ScientificSpectrumPlot } from './components/ScientificSpectrumPlot'
import { JablonskiDiagram } from './components/JablonskiDiagram'
import { InteractiveHelp } from './components/InteractiveHelp'
import { EnsemblePopulationPlot, MassSpectrumPlot, PeriodicCellPlot } from './components/ProfileAnalysisPlots'
import {
  CALCULATION_PROFILES,
  CalculationProfileSwitch,
  type CalculationProfile,
  type CalculationProfileId,
} from './components/CalculationProfileSwitch'
import {
  lookupPubChem,
  downloadQuantumReport,
  interpretQuantumResult,
  predictSpectrum,
  prepareMolecule,
  reverseAnalyze,
  runScreening,
  submitQuantumJob,
  waitForQuantumJob,
  type MoleculePreparation,
  type QuantumResult,
  type QuantumInterpretation,
  type QuantumJobProgress,
} from './lib/api'

type Mode = 'design' | 'analytics' | 'screening' | 'quantum'
type QuantumView = 'structure' | 'ir' | 'uv' | 'jablonski' | 'mass' | 'environment' | 'periodic'

const quantumViews: Array<{ id: QuantumView; label: string; description: string }> = [
  { id: 'structure', label: '3D и электроника', description: 'Молекула, плотность и дескрипторы' },
  { id: 'ir', label: 'ИК-спектр', description: 'Колебательные моды' },
  { id: 'uv', label: 'UV-Vis', description: 'Электронные переходы' },
  { id: 'jablonski', label: 'Диаграмма Яблонского', description: 'Уровни возбуждённых состояний' },
  { id: 'mass', label: 'Масс-спектр', description: 'Фрагменты и относительные интенсивности' },
  { id: 'environment', label: 'Среда и ансамбль', description: 'QM/MM-заряды и конформеры' },
  { id: 'periodic', label: 'Периодика', description: 'Ячейка и суперструктура' },
]

function statusBadge(status?: string) {
  if (status === 'SUCCESS') return <Badge variant="success">ГОТОВО</Badge>
  if (status === 'PARKED') return <Badge variant="warn">ОТЛОЖЕНО</Badge>
  if (status === 'FAILED') return <Badge variant="danger">ОШИБКА</Badge>
  return <Badge>ГОТОВ К РАБОТЕ</Badge>
}

function messageFromError(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function App() {
  const [mode, setMode] = useState<Mode>('quantum')
  const [name, setName] = useState('Аспирин')
  const [smiles, setSmiles] = useState('CC(=O)Oc1ccccc1C(=O)O')
  const [solvent, setSolvent] = useState('DMSO-d6')
  const [eps, setEps] = useState(46.7)
  const [ri, setRi] = useState(1.47)
  const [temperature, setTemperature] = useState(298.15)
  const [result, setResult] = useState<any>(null)
  const [screening, setScreening] = useState<any>(null)
  const [reverse, setReverse] = useState<any>(null)
  const [molecule, setMolecule] = useState<MoleculePreparation | null>(null)
  const [quantum, setQuantum] = useState<QuantumResult | null>(null)
  const [quantumInterpretation, setQuantumInterpretation] = useState<QuantumInterpretation | null>(null)
  const [quantumTaskId, setQuantumTaskId] = useState<string | null>(null)
  const [calculationProfile, setCalculationProfile] = useState<CalculationProfileId>('ir_uv')
  const [quantumView, setQuantumView] = useState<QuantumView>('structure')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [quantumProgress, setQuantumProgress] = useState<number>(0)
  const [quantumStep, setQuantumStep] = useState<string>('')
  const [quantumMessage, setQuantumMessage] = useState<string>('')
  const [helpOpen, setHelpOpen] = useState(() => new URLSearchParams(window.location.search).get('help') === '1')

  const candidates = useMemo(() => [
    { name: 'Этанол', smiles: 'CCO' },
    { name: 'Бутанол', smiles: 'CCCCO' },
    { name: 'Изопропанол', smiles: 'CC(O)C' },
    { name: 'Ацетон', smiles: 'CC(=O)C' },
    { name: 'Толуол', smiles: 'Cc1ccccc1' },
    { name: 'Аспирин', smiles: 'CC(=O)Oc1ccccc1C(=O)O' },
    { name: 'Тест границы применимости', smiles: 'CCCCCCCCCCCCCCCCCCCCCCCCO' },
  ], [])

  const selectedProfile = CALCULATION_PROFILES.find(profile => profile.id === calculationProfile)!

  function predictionPayload() {
    return {
      structure: { name, smiles, source: 'manual' as const },
      environment: {
        solvent_name: solvent,
        solvent_model: 'PCM' as const,
        solvent_eps: eps,
        solvent_ri: ri,
        temperature_k: 298.15,
      },
      instrument: { spectroscopy_type: '13C_NMR', frequency_mhz: 400, spectral_points: 1200 },
      compute_mode: 'fast_surrogate',
    }
  }

  async function runPrediction() {
    setLoading(true)
    setError(null)
    try {
      setResult(await predictSpectrum(predictionPayload()))
      setMode('design')
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function runScreeningJob() {
    setLoading(true)
    setError(null)
    try {
      setScreening(await runScreening(candidates))
      setMode('screening')
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function runReverseJob() {
    setLoading(true)
    setError(null)
    try {
      let source = result?.spectrum
      if (!source) {
        const prediction = await predictSpectrum(predictionPayload())
        setResult(prediction)
        source = prediction.spectrum
      }
      if (!source) throw new Error('Для обратного анализа сначала требуется рассчитанный спектр.')
      setReverse(await reverseAnalyze(source.x_axis, source.y_axis))
      setMode('analytics')
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function prepareStructure() {
    setLoading(true)
    setError(null)
    try {
      setMolecule(await prepareMolecule(name, smiles))
      setQuantum(null)
      setQuantumInterpretation(null)
      setMode('quantum')
      setQuantumView('structure')
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function loadPubChem() {
    setLoading(true)
    setError(null)
    try {
      const reference = await lookupPubChem(name || smiles)
      const referenceSmiles = reference.isomeric_smiles || reference.canonical_smiles
      if (!referenceSmiles) throw new Error('В записи PubChem отсутствует представление SMILES.')
      const referenceName = reference.name || name
      setName(referenceName)
      setSmiles(referenceSmiles)
      setMolecule(await prepareMolecule(referenceName, referenceSmiles))
      setQuantum(null)
      setQuantumInterpretation(null)
      setMode('quantum')
      setQuantumView('structure')
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  function selectCalculationProfile(profile: CalculationProfile) {
    setCalculationProfile(profile.id)
    setQuantumView(profile.defaultView)
    setMode('quantum')
    setError(profile.available ? null : `Профиль «${profile.label}» показан в дорожной карте, но его расчётный движок ещё не подключён.`)
  }

  async function runQuantumJob() {
    if (!selectedProfile.available) {
      setError(`Профиль «${selectedProfile.label}» пока недоступен для запуска.`)
      return
    }
    setLoading(true)
    setError(null)
    setMode('quantum')
    setQuantumProgress(0)
    setQuantumStep('init')
    setQuantumMessage('Подготовка задачи…')
    try {
      let prepared = molecule
      if (!prepared || prepared.input_smiles !== smiles) {
        prepared = await prepareMolecule(name, smiles)
        setMolecule(prepared)
      }
      const submission = await submitQuantumJob(name, smiles, {
        profile: selectedProfile.id,
        harmonicModes: selectedProfile.harmonicModes,
        excitedStates: selectedProfile.excitedStates,
        solventName: solvent,
        solventEps: eps,
        temperatureK: temperature,
        parallelJobs: 0,
      })
      setQuantumTaskId(submission.task_id)
      const quantumResult = await waitForQuantumJob(submission.task_id, (p: QuantumJobProgress) => {
        setQuantumProgress(p.progress)
        setQuantumStep(p.step)
        setQuantumMessage(p.message)
      })
      setQuantum(quantumResult)
      setQuantumInterpretation(await interpretQuantumResult(selectedProfile.id, quantumResult))
      setQuantumView(selectedProfile.defaultView)
    } catch (requestError) {
      setError(messageFromError(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function exportQuantumReport() {
    if (!molecule || !quantum) {
      setError('Сначала выполните расчёт и подготовьте молекулу.')
      return
    }
    try {
      await downloadQuantumReport({
        title: `Q2SC: ${name}`,
        profile: selectedProfile.id,
        molecule,
        result: quantum,
        interpretation: quantumInterpretation,
      })
    } catch (requestError) {
      setError(messageFromError(requestError))
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-300"><Atom size={22} /></div>
            <div>
              <h1 className="text-lg font-semibold">Q2SC — вычислительная химия</h1>
              <p className="text-xs text-slate-400">Молекулярная визуализация, QSAR и квантовая спектроскопия</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {statusBadge(result?.status)}
            <Badge>{mode === 'quantum' ? 'КВАНТОВЫЙ РАСЧЁТ' : mode.toUpperCase()}</Badge>
            <Button variant="secondary" className="gap-2" onClick={() => setHelpOpen(true)}>
              <HelpCircle size={16} /> Справка
            </Button>
          </div>
        </div>
      </header>

      <main className="grid gap-4 p-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <Card>
            <CardHeader><CardTitle>Рабочий сценарий</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Button variant={mode === 'design' ? 'default' : 'secondary'} className="w-full justify-start gap-2" onClick={() => setMode('design')}><FlaskConical size={16} /> Прогноз спектра</Button>
              <Button variant={mode === 'analytics' ? 'default' : 'secondary'} className="w-full justify-start gap-2" onClick={() => setMode('analytics')}><BrainCircuit size={16} /> Обратный анализ</Button>
              <Button variant={mode === 'screening' ? 'default' : 'secondary'} className="w-full justify-start gap-2" onClick={() => setMode('screening')}><Network size={16} /> Пакетный скрининг</Button>
              <Button variant={mode === 'quantum' ? 'default' : 'secondary'} className="w-full justify-start gap-2" onClick={() => setMode('quantum')}><Box size={16} /> Квантовые расчёты</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Структура и окружение</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <label className="block space-y-1 text-xs text-slate-400">Название<Input value={name} onChange={event => setName(event.target.value)} /></label>
              <label className="block space-y-1 text-xs text-slate-400">SMILES<Input value={smiles} onChange={event => setSmiles(event.target.value)} /></label>
              <label className="block space-y-1 text-xs text-slate-400">Растворитель<Input value={solvent} onChange={event => setSolvent(event.target.value)} /></label>
              <div className="grid grid-cols-2 gap-2">
                <label className="block space-y-1 text-xs text-slate-400">Диэлектрическая проницаемость<Input type="number" value={eps} onChange={event => setEps(Number(event.target.value))} /></label>
                <label className="block space-y-1 text-xs text-slate-400">Показатель преломления<Input type="number" value={ri} onChange={event => setRi(Number(event.target.value))} /></label>
              </div>
              <label className="block space-y-1 text-xs text-slate-400">Температура, K<Input type="number" value={temperature} onChange={event => setTemperature(Number(event.target.value))} /></label>
              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" className="gap-2" onClick={prepareStructure} disabled={loading}><Box size={16} /> Подготовить 2D/3D</Button>
                <Button variant="secondary" className="gap-2" onClick={loadPubChem} disabled={loading}><Search size={16} /> Найти в PubChem</Button>
              </div>
              <Button className="w-full gap-2" onClick={runQuantumJob} disabled={loading || !selectedProfile.available}>
                {loading ? <Loader2 className="animate-spin" size={16} /> : <Atom size={16} />}
                Запустить: {selectedProfile.shortLabel}
              </Button>
              <div className="grid grid-cols-3 gap-2">
                <Button variant="secondary" title="Быстрый QSAR-прогноз" onClick={runPrediction} disabled={loading}><Activity size={16} /></Button>
                <Button variant="secondary" title="Пакетный скрининг" onClick={runScreeningJob} disabled={loading}><GitBranch size={16} /></Button>
                <Button variant="secondary" title="Обратный анализ" onClick={runReverseJob} disabled={loading}><Database size={16} /></Button>
              </div>
              {quantumTaskId && <div className="break-all text-[10px] text-slate-500">Задача: {quantumTaskId}</div>}
              {error && <div className="rounded-md border border-red-800 bg-red-950 p-3 text-xs leading-relaxed text-red-200">{error}</div>}
            </CardContent>
          </Card>
        </aside>

        <section className="min-w-0 space-y-4">
          {mode === 'design' && (
            <div className="grid gap-4 xl:grid-cols-3">
              <Card className="xl:col-span-2">
                <CardHeader><CardTitle>Прогнозируемый спектр</CardTitle></CardHeader>
                <CardContent><SpectrumPlot spectrum={result?.spectrum} /></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Обоснование прогноза</CardTitle></CardHeader>
                <CardContent className="space-y-3 text-sm text-slate-300">
                  <div>Область применимости: {result?.ad?.decision ?? '—'}</div>
                  <div>T² Хотеллинга: {result?.ad?.t2_hotelling ?? '—'} / {result?.ad?.t2_critical ?? '—'}</div>
                  <div>Q-остаток: {result?.ad?.q_residual ?? '—'} / {result?.ad?.q_critical ?? '—'}</div>
                  <div className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-xs leading-relaxed text-slate-400">
                    {result?.interpretation?.expert_summary ?? 'Запустите прогноз, чтобы получить интерпретацию результата.'}
                  </div>
                </CardContent>
              </Card>
              <Card className="xl:col-span-3">
                <CardHeader><CardTitle>Журнал расчёта</CardTitle></CardHeader>
                <CardContent><pre className="max-h-60 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(result?.audit_trail ?? [], null, 2)}</pre></CardContent>
              </Card>
            </div>
          )}

          {mode === 'screening' && (
            <Card>
              <CardHeader><CardTitle>Пакетный скрининг и спектральная тепловая карта</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-2 text-sm">
                  <Badge variant="success">Принято: {screening?.accepted ?? 0}</Badge>
                  <Badge variant="warn">Отложено: {screening?.parked ?? 0}</Badge>
                  <Badge variant="danger">Ошибки: {screening?.failed ?? 0}</Badge>
                </div>
                <Heatmap data={screening} />
              </CardContent>
            </Card>
          )}

          {mode === 'analytics' && (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card>
                <CardHeader><CardTitle>Обнаруженные пики</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {(reverse?.detected_peaks ?? []).map((peak: any, index: number) => (
                    <div className="rounded-md border border-slate-800 p-2 text-sm" key={index}>{peak.position} ppm / {peak.intensity}</div>
                  ))}
                  {!reverse && <div className="text-sm text-slate-500">Запустите обратный анализ для поиска пиков.</div>}
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle>Ранжированные кандидаты</CardTitle></CardHeader>
                <CardContent className="space-y-2">
                  {(reverse?.candidates ?? []).map((candidate: any) => (
                    <div className="rounded-md border border-slate-800 p-2 text-sm" key={candidate.rank}>
                      <b>#{candidate.rank} {candidate.name}</b><br />
                      Оценка: {candidate.match_score}; Δпика: {candidate.delta_peak}; {candidate.status}
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          )}

          {mode === 'quantum' && (
            <QuantumWorkspace
              selectedProfile={selectedProfile}
              calculationProfile={calculationProfile}
              quantumView={quantumView}
              molecule={molecule}
              quantum={quantum}
              interpretation={quantumInterpretation}
              loading={loading}
              progress={quantumProgress}
              progressStep={quantumStep}
              progressMessage={quantumMessage}
              onSelectProfile={selectCalculationProfile}
              onSelectView={setQuantumView}
              onRun={runQuantumJob}
              onOpenHelp={() => setHelpOpen(true)}
              onDownloadReport={exportQuantumReport}
            />
          )}
        </section>
      </main>

      <InteractiveHelp open={helpOpen} onClose={() => setHelpOpen(false)} onOpenQuantum={() => setMode('quantum')} />
    </div>
  )
}

function QuantumWorkspace({
  selectedProfile,
  calculationProfile,
  quantumView,
  molecule,
  quantum,
  interpretation,
  loading,
  progress,
  progressStep,
  progressMessage,
  onSelectProfile,
  onSelectView,
  onRun,
  onOpenHelp,
  onDownloadReport,
}: {
  selectedProfile: CalculationProfile
  calculationProfile: CalculationProfileId
  quantumView: QuantumView
  molecule: MoleculePreparation | null
  quantum: QuantumResult | null
  interpretation: QuantumInterpretation | null
  loading: boolean
  progress: number
  progressStep: string
  progressMessage: string
  onSelectProfile: (profile: CalculationProfile) => void
  onSelectView: (view: QuantumView) => void
  onRun: () => void
  onOpenHelp: () => void
  onDownloadReport: () => void
}) {
  return (
    <div className="space-y-4">
      <Card className="border-cyan-950">
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base">1. Выберите расчётный профиль</CardTitle>
            <p className="mt-1 text-xs text-slate-400">Доступные профили можно запускать. Будущие профили отмечены жёлтым статусом.</p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" className="gap-2" onClick={onOpenHelp}><HelpCircle size={16} /> Что выбрать?</Button>
            <Button variant="secondary" className="gap-2" onClick={onDownloadReport} disabled={!quantum}><Download size={16} /> PDF-отчёт</Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <CalculationProfileSwitch value={calculationProfile} onChange={onSelectProfile} />
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold">{selectedProfile.label}</div>
              <div className="text-xs text-slate-400">{selectedProfile.description}</div>
              {loading && (
                <div className="mt-2 space-y-1">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="progress-bar-fill"
                      style={{ '--q-bar-pct': `${Math.max(3, progress)}%` } as React.CSSProperties}
                    />
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-2">
                    <span className={progressStep === 'queued' || progressStep === 'pending' ? 'text-yellow-400' : ''}>
                      {progressMessage || progressStep || 'Подготовка…'}
                    </span>
                    {progress > 0 && <span className="text-cyan-400">{progress}%</span>}
                  </div>
                </div>
              )}
            </div>
            <Button className="gap-2" onClick={onRun} disabled={loading || !selectedProfile.available}>
              {loading ? <Loader2 className="animate-spin" size={16} /> : <Atom size={16} />}
              {loading ? 'Выполняется расчёт…' : 'Запустить расчёт'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="sticky top-[73px] z-20 border-cyan-900/70 bg-slate-950/95 backdrop-blur">
        <CardHeader>
          <CardTitle className="text-base">2. Выберите представление результата</CardTitle>
        </CardHeader>
        <CardContent>
          <div role="tablist" className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            {quantumViews.map(view => (
              <button
                key={view.id}
                type="button"
                role="tab"
                aria-selected={quantumView === view.id ? 'true' : 'false'}
                onClick={() => onSelectView(view.id)}
                className={[
                  'rounded-lg border px-4 py-3 text-left transition',
                  quantumView === view.id
                    ? 'border-cyan-400 bg-cyan-950/70 text-cyan-50 ring-1 ring-cyan-400/30'
                    : 'border-slate-700 bg-slate-900 text-slate-200 hover:border-slate-500',
                ].join(' ')}
              >
                <div className="text-sm font-semibold">{view.label}</div>
                <div className="mt-1 text-[11px] text-slate-400">{view.description}</div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {!quantum && (
        <Card className="border-dashed border-slate-700">
          <CardContent className="grid gap-3 pt-6 sm:grid-cols-2 xl:grid-cols-4">
            {[
              ['1', 'Введите SMILES', 'Структура задаётся в левой панели.'],
              ['2', 'Выберите профиль', 'Для всех диаграмм выберите «ИК + UV-Vis».'],
              ['3', 'Запустите задачу', 'Расчёт выполняется фоновым PySCF-worker.'],
              ['4', 'Откройте вкладку', 'Графики появятся после завершения задачи.'],
            ].map(([number, title, text]) => (
              <div key={number} className="rounded-lg bg-slate-900/60 p-3">
                <div className="mb-2 flex h-6 w-6 items-center justify-center rounded-full bg-cyan-400 text-xs font-bold text-slate-950">{number}</div>
                <div className="text-sm font-medium">{title}</div>
                <div className="mt-1 text-xs leading-relaxed text-slate-400">{text}</div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {quantumView === 'structure' && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader><CardTitle>3D-молекула и электронная плотность</CardTitle></CardHeader>
            <CardContent>
              <MoleculeViewer
                molBlock={molecule?.mol_block}
                densityCube={quantum?.cube_artifacts?.electron_density}
                pointCharges={quantum?.qmmm_analysis?.point_charges}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Рассчитанное состояние</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-300">
              <div>Формула: {molecule?.formula ?? '—'}</div>
              <div>Подготовка: {molecule?.preparation_method ?? '—'}</div>
              <div>Энергия конформера: {molecule?.conformer_energy_kcal_mol ?? '—'} ккал/моль</div>
              <div>Движок: {quantum ? `${quantum.engine} ${quantum.engine_version}` : '—'}</div>
              <div>Уровень: {quantum ? `${quantum.method}/${quantum.basis}` : '—'}</div>
              <div>Электронная энергия: {quantum?.electronic_energy_hartree ?? '—'} Eh</div>
              <div>HOMO / LUMO: {quantum?.homo_ev != null && quantum?.lumo_ev != null ? `${quantum.homo_ev} / ${quantum.lumo_ev} эВ` : '—'}</div>
              <div>Щель: {quantum?.gap_ev ?? '—'} эВ</div>
              <div>Диполь: {quantum ? quantum.dipole_debye.map(value => value.toFixed(3)).join(', ') : '—'} D</div>
              {quantum?.provenance.limitations.map(item => (
                <div key={item} className="rounded border border-amber-900 bg-amber-950/40 p-2 text-xs text-amber-200">{item}</div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>2D-структура</CardTitle></CardHeader>
            <CardContent>
              {molecule
                ? <div className="rounded bg-white p-2" dangerouslySetInnerHTML={{ __html: molecule.svg_2d }} />
                : <EmptyState text="Сначала подготовьте структуру молекулы." />}
            </CardContent>
          </Card>
          <Card className="xl:col-span-2">
            <CardHeader><CardTitle>Дескрипторы и атомные заряды</CardTitle></CardHeader>
            <CardContent className="grid gap-2 text-xs text-slate-300 sm:grid-cols-2 xl:grid-cols-3">
              {Object.entries(molecule?.descriptors ?? {}).map(([key, value]) => (
                <div key={key} className="rounded border border-slate-800 p-2"><b>{key}</b><br />{value}</div>
              ))}
              {(quantum?.mulliken_charges ?? []).map((charge, index) => (
                <div key={`charge-${index}`} className="rounded border border-cyan-950 p-2">Атом {index}<br />q = {charge.toFixed(4)}</div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {quantumView === 'ir' && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader><CardTitle>Рассчитанный ИК-спектр</CardTitle></CardHeader>
            <CardContent>
              <ScientificSpectrumPlot
                spectrum={quantum?.vibrational_analysis?.spectrum}
                title="Гармонические моды и относительная ИК-интенсивность"
                reverseX
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Нормальные моды</CardTitle></CardHeader>
            <CardContent className="max-h-80 space-y-1 overflow-auto text-xs text-slate-300">
              {(quantum?.vibrational_analysis?.modes ?? []).map(vibration => (
                <div key={vibration.index} className="rounded border border-slate-800 p-2">
                  Мода {vibration.index + 1}: {vibration.frequency_cm_1.toFixed(2)} см⁻¹ {vibration.imaginary ? '(мнимая)' : ''}<br />
                  Относительная I: {vibration.relative_ir_intensity.toFixed(4)}
                </div>
              ))}
              {!quantum?.vibrational_analysis && <EmptyState text="Запустите профиль «ИК» или «ИК + UV-Vis»." />}
            </CardContent>
          </Card>
        </div>
      )}

      {quantumView === 'uv' && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader><CardTitle>Рассчитанный UV-Vis-спектр</CardTitle></CardHeader>
            <CardContent>
              <ScientificSpectrumPlot spectrum={quantum?.excited_state_analysis?.spectrum} title="Вертикальные электронные переходы" />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Электронные переходы</CardTitle></CardHeader>
            <CardContent className="max-h-80 space-y-1 overflow-auto text-xs text-slate-300">
              {(quantum?.excited_state_analysis?.states ?? []).map(state => (
                <div key={state.state} className="rounded border border-slate-800 p-2">
                  {state.state}: {state.energy_ev.toFixed(3)} эВ<br />
                  {state.wavelength_nm.toFixed(1)} нм; f = {state.oscillator_strength.toFixed(5)}
                </div>
              ))}
              {!quantum?.excited_state_analysis && <EmptyState text="Запустите профиль «UV-Vis» или «ИК + UV-Vis»." />}
            </CardContent>
          </Card>
        </div>
      )}

      {quantumView === 'jablonski' && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Card className="xl:col-span-2">
            <CardHeader><CardTitle>Диаграмма Яблонского</CardTitle></CardHeader>
            <CardContent><JablonskiDiagram states={quantum?.excited_state_analysis?.states} /></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Область применимости модели</CardTitle></CardHeader>
            <CardContent className="space-y-2 text-xs text-slate-300">
              {(quantum?.excited_state_analysis?.jablonski_model.limitations ?? [
                'Запустите профиль UV-Vis для расчёта возбуждённых состояний.',
                'Текущая схема показывает вертикальные синглетные переходы из основного состояния.',
              ]).map(item => (
                <div key={item} className="rounded border border-amber-900 bg-amber-950/40 p-2 text-amber-200">{item}</div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {quantumView === 'mass' && (
        <Card>
          <CardHeader><CardTitle>Фрагментационный масс-спектр</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <MassSpectrumPlot
              spectrum={quantum?.mass_spectrum_analysis?.spectrum}
              fragments={quantum?.mass_spectrum_analysis?.fragments}
            />
            {(quantum?.mass_spectrum_analysis?.limitations ?? []).map(item => (
              <div key={item} className="rounded border border-amber-900 bg-amber-950/40 p-2 text-xs text-amber-200">{item}</div>
            ))}
          </CardContent>
        </Card>
      )}

      {quantumView === 'environment' && (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>QM/MM-подобное электростатическое окружение</CardTitle></CardHeader>
            <CardContent>
              <MoleculeViewer
                molBlock={molecule?.mol_block}
                pointCharges={quantum?.qmmm_analysis?.point_charges}
              />
              {!quantum?.qmmm_analysis && <EmptyState text="Для отображения внешних зарядов запустите профиль QM/MM." />}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Больцмановский ансамбль конформеров</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <EnsemblePopulationPlot conformers={quantum?.ensemble_analysis?.conformers} />
              {quantum?.ensemble_analysis && (
                <div className="text-xs text-slate-400">
                  T = {quantum.ensemble_analysis.temperature_k.toFixed(2)} K · эффективное число конформеров: {quantum.ensemble_analysis.effective_conformer_count.toFixed(2)}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {quantumView === 'periodic' && (
        <Card>
          <CardHeader><CardTitle>Периодическая суперъячейка</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <PeriodicCellPlot
              vectors={quantum?.periodic_analysis?.lattice_vectors_angstrom}
              atomCount={quantum?.periodic_analysis?.atoms.length}
            />
            {(quantum?.periodic_analysis?.limitations ?? []).map(item => (
              <div key={item} className="rounded border border-amber-900 bg-amber-950/40 p-2 text-xs text-amber-200">{item}</div>
            ))}
          </CardContent>
        </Card>
      )}

      {interpretation && (
        <Card>
          <CardHeader><CardTitle>Интерпретирующий слой</CardTitle></CardHeader>
          <CardContent className="grid gap-4 xl:grid-cols-3">
            <div className="rounded-lg border border-cyan-900 bg-cyan-950/30 p-4 text-sm leading-relaxed text-cyan-50">{interpretation.summary}</div>
            <div className="space-y-2 text-xs text-slate-300">
              <b>Наблюдения</b>
              {interpretation.findings.map(item => <div key={item} className="rounded border border-slate-800 p-2">{item}</div>)}
            </div>
            <div className="space-y-2 text-xs text-slate-300">
              <b>Рекомендации</b>
              {interpretation.recommendations.map(item => <div key={item} className="rounded border border-slate-800 p-2">{item}</div>)}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function EmptyState({ text }: { text: string }) {
  return <div className="flex min-h-24 items-center justify-center rounded-lg border border-dashed border-slate-800 p-4 text-center text-sm text-slate-500">{text}</div>
}
