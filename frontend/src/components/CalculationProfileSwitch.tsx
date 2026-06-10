import { Badge } from './ui/badge'

export type CalculationProfileId =
  | 'electronic'
  | 'ir'
  | 'uv_vis'
  | 'ir_uv'
  | 'qcxms'
  | 'qmmm'
  | 'solvent_ensemble'
  | 'periodic'
  | 'absolute_intensity'

export type CalculationProfile = {
  id: CalculationProfileId
  label: string
  shortLabel: string
  description: string
  available: boolean
  harmonicModes: boolean
  excitedStates: boolean
  defaultView: 'structure' | 'ir' | 'uv' | 'jablonski' | 'mass' | 'environment' | 'periodic'
  methodLevel: string
}

export const CALCULATION_PROFILES: CalculationProfile[] = [
  {
    id: 'electronic',
    label: 'Электронная структура',
    shortLabel: 'Электронная структура',
    description: 'Энергия HF, орбитали, заряды Малликена и электронная плотность.',
    available: true,
    harmonicModes: false,
    excitedStates: false,
    defaultView: 'structure',
    methodLevel: 'PySCF HF/DFT',
  },
  {
    id: 'ir',
    label: 'ИК-спектр',
    shortLabel: 'ИК',
    description: 'Гармонические нормальные моды и относительные ИК-интенсивности.',
    available: true,
    harmonicModes: true,
    excitedStates: false,
    defaultView: 'ir',
    methodLevel: 'Гармонический анализ PySCF',
  },
  {
    id: 'uv_vis',
    label: 'UV-Vis и диаграмма Яблонского',
    shortLabel: 'UV-Vis + Яблонский',
    description: 'Вертикальные синглетные возбуждения, спектр поглощения и уровни состояний.',
    available: true,
    harmonicModes: false,
    excitedStates: true,
    defaultView: 'uv',
    methodLevel: 'TDHF/TDDFT',
  },
  {
    id: 'ir_uv',
    label: 'ИК + UV-Vis',
    shortLabel: 'ИК + UV-Vis',
    description: 'Совместный расчёт колебательных и электронных переходов.',
    available: true,
    harmonicModes: true,
    excitedStates: true,
    defaultView: 'ir',
    methodLevel: 'Гессиан + TDHF/TDDFT',
  },
  {
    id: 'qcxms',
    label: 'Масс-спектр QCxMS',
    shortLabel: 'QCxMS',
    description: 'Исполняемый скрининг односвязной фрагментации; адаптер для будущего QCxMS.',
    available: true,
    harmonicModes: false,
    excitedStates: false,
    defaultView: 'mass',
    methodLevel: 'RDKit bond-cleavage screen',
  },
  {
    id: 'qmmm',
    label: 'QM/MM',
    shortLabel: 'QM/MM',
    description: 'Квантовая область в электростатическом поле внешних точечных зарядов.',
    available: true,
    harmonicModes: false,
    excitedStates: false,
    defaultView: 'environment',
    methodLevel: 'PySCF electrostatic embedding',
  },
  {
    id: 'solvent_ensemble',
    label: 'Явный ансамбль растворителя',
    shortLabel: 'Растворитель',
    description: 'Больцмановское усреднение по ансамблю конформеров при заданной температуре.',
    available: true,
    harmonicModes: false,
    excitedStates: false,
    defaultView: 'environment',
    methodLevel: 'ETKDGv3/MMFF94 ensemble',
  },
  {
    id: 'periodic',
    label: 'Периодический расчёт',
    shortLabel: 'Периодика',
    description: 'Подготовка и проверка периодической суперъячейки для последующего PBC-расчёта.',
    available: true,
    harmonicModes: false,
    excitedStates: false,
    defaultView: 'periodic',
    methodLevel: 'Periodic geometry preparation',
  },
  {
    id: 'absolute_intensity',
    label: 'Абсолютные интенсивности',
    shortLabel: 'Абс. интенсивности',
    description: 'Оценка интегральных ИК-интенсивностей из производных дипольного момента.',
    available: true,
    harmonicModes: true,
    excitedStates: true,
    defaultView: 'ir',
    methodLevel: 'Finite-difference intensity estimate',
  },
]

export function CalculationProfileSwitch({
  value,
  onChange,
}: {
  value: CalculationProfileId
  onChange: (profile: CalculationProfile) => void
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {CALCULATION_PROFILES.map(profile => {
        const selected = profile.id === value
        return (
          <button
            key={profile.id}
            type="button"
            aria-pressed={selected ? 'true' : 'false'}
            onClick={() => onChange(profile)}
            title={profile.description}
            className={[
              'min-h-24 rounded-lg border p-3 text-left transition',
              selected
                ? 'border-cyan-400 bg-cyan-950/60 ring-1 ring-cyan-400/30'
                : 'border-slate-800 bg-slate-950/50 hover:border-slate-600 hover:bg-slate-900',
            ].join(' ')}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm font-semibold text-slate-100">{profile.shortLabel}</span>
              <Badge variant={profile.available ? 'success' : 'warn'}>{profile.available ? 'Запускается' : 'В плане'}</Badge>
            </div>
            <div className="mt-2 text-[11px] leading-relaxed text-slate-400">{profile.description}</div>
            <div className="mt-2 text-[10px] uppercase tracking-wide text-cyan-400/80">{profile.methodLevel}</div>
          </button>
        )
      })}
    </div>
  )
}
