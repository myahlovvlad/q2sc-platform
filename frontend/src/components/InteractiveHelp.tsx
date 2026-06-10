import { useState } from 'react'
import { Atom, BookOpen, ChartNoAxesCombined, CircleAlert, Play, X } from 'lucide-react'
import { Button } from './ui/button'

type HelpTopic = 'start' | 'profiles' | 'results' | 'limits'

const topics: Array<{ id: HelpTopic; label: string; icon: typeof Atom }> = [
  { id: 'start', label: 'Быстрый старт', icon: Play },
  { id: 'profiles', label: 'Профили расчёта', icon: Atom },
  { id: 'results', label: 'Графики и вкладки', icon: ChartNoAxesCombined },
  { id: 'limits', label: 'Ограничения методов', icon: CircleAlert },
]

export function InteractiveHelp({
  open,
  onClose,
  onOpenQuantum,
}: {
  open: boolean
  onClose: () => void
  onOpenQuantum: () => void
}) {
  const [topic, setTopic] = useState<HelpTopic>('start')
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Справка">
      <div className="flex max-h-[88vh] w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl">
        <aside className="w-60 shrink-0 border-r border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-5 flex items-center gap-2 text-base font-semibold">
            <BookOpen size={18} className="text-cyan-300" />
            Интерактивная справка
          </div>
          <div className="space-y-2">
            {topics.map(item => {
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTopic(item.id)}
                  className={[
                    'flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition',
                    topic === item.id ? 'bg-cyan-950 text-cyan-100' : 'text-slate-300 hover:bg-slate-800',
                  ].join(' ')}
                >
                  <Icon size={16} />
                  {item.label}
                </button>
              )
            })}
          </div>
        </aside>

        <section className="min-w-0 flex-1 overflow-y-auto p-6">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-400">Q2SC</div>
              <h2 className="mt-1 text-xl font-semibold">Как работать с приложением</h2>
            </div>
            <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Закрыть справку">
              <X size={20} />
            </button>
          </div>

          {topic === 'start' && (
            <div className="space-y-4">
              <p className="text-sm leading-relaxed text-slate-300">Для получения ИК- или UV-Vis-спектра нужен квантовый расчёт. Подготовка 2D/3D-структуры сама по себе спектры не создаёт.</p>
              <div className="grid gap-3 md:grid-cols-2">
                {[
                  ['1', 'Введите молекулу', 'Укажите название и корректную строку SMILES.'],
                  ['2', 'Выберите профиль', 'Например, «ИК + UV-Vis» в верхней панели квантового раздела.'],
                  ['3', 'Запустите расчёт', 'Нажмите основную кнопку запуска и дождитесь окончания задачи.'],
                  ['4', 'Откройте результат', 'Переключайтесь между 3D, ИК, UV-Vis и диаграммой Яблонского.'],
                ].map(([number, title, text]) => (
                  <div key={number} className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
                    <div className="mb-2 flex h-7 w-7 items-center justify-center rounded-full bg-cyan-400 font-bold text-slate-950">{number}</div>
                    <div className="font-medium">{title}</div>
                    <div className="mt-1 text-xs leading-relaxed text-slate-400">{text}</div>
                  </div>
                ))}
              </div>
              <Button onClick={() => { onOpenQuantum(); onClose() }} className="gap-2"><Atom size={16} /> Перейти к квантовым расчётам</Button>
            </div>
          )}

          {topic === 'profiles' && (
            <div className="space-y-3 text-sm text-slate-300">
              <HelpRow title="Электронная структура" text="Энергия, HOMO/LUMO, дипольный момент, заряды и куб электронной плотности." />
              <HelpRow title="ИК" text="Гармонический анализ нормальных мод и относительных ИК-интенсивностей." />
              <HelpRow title="UV-Vis + Яблонский" text="Вертикальные синглетные возбуждения, осцилляторные силы и схема уровней." />
              <HelpRow title="ИК + UV-Vis" text="Оба спектроскопических расчёта в одной задаче. Он тяжелее и выполняется дольше." />
              <div className="rounded-lg border border-amber-900 bg-amber-950/40 p-3 text-amber-200">Дополнительные профили теперь исполняются как проверяемые приближённые процессы: фрагментационный скрининг, электростатическое встраивание, конформационный ансамбль и подготовка периодической ячейки. Интерфейс всегда показывает уровень метода и не подменяет ими полноценные QCxMS, поляризуемый QM/MM или periodic DFT.</div>
            </div>
          )}

          {topic === 'results' && (
            <div className="space-y-3 text-sm text-slate-300">
              <HelpRow title="3D и электроника" text="Вращайте молекулу мышью, масштабируйте колесом. После расчёта может отображаться изоповерхность электронной плотности." />
              <HelpRow title="ИК-спектр" text="Ось волновых чисел направлена от больших значений к малым. Справа приведён список нормальных мод." />
              <HelpRow title="UV-Vis" text="Показана огибающая вертикальных электронных переходов и таблица энергий, длин волн и осцилляторных сил." />
              <HelpRow title="Диаграмма Яблонского" text="Линии соответствуют рассчитанным синглетным состояниям, стрелки — вертикальным переходам из S0." />
              <div className="rounded-lg border border-cyan-900 bg-cyan-950/30 p-3 text-cyan-100">Вкладки результатов закреплены непосредственно над областью графика и видны сразу после входа в раздел «Квантовые расчёты».</div>
            </div>
          )}

          {topic === 'limits' && (
            <div className="space-y-3 text-sm text-slate-300">
              <HelpRow title="ИК" text="Сейчас используется гармоническое приближение и относительная, а не абсолютная шкала интенсивности." />
              <HelpRow title="UV-Vis" text="Рассчитываются вертикальные синглетные возбуждения. Триплеты, спин-орбитальное взаимодействие и релаксация возбуждённого состояния не включены." />
              <HelpRow title="Среда" text="Обычный электронный профиль использует одиночный конформер. Профили QM/MM и растворителя передают диэлектрическую проницаемость, температуру и параметры окружения в расчётную задачу." />
              <HelpRow title="Время" text="Расчёт быстро дорожает с размером молекулы. Для проверки интерфейса лучше начинать с воды, этанола или ацетона." />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function HelpRow({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
      <div className="font-medium text-slate-100">{title}</div>
      <div className="mt-1 leading-relaxed text-slate-400">{text}</div>
    </div>
  )
}
