import { cn } from '../../lib/utils'

export function Badge({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'default' | 'success' | 'warn' | 'danger' }) {
  const map = {
    default: 'border-slate-700 bg-slate-900 text-slate-300',
    success: 'border-emerald-800 bg-emerald-950 text-emerald-200',
    warn: 'border-amber-800 bg-amber-950 text-amber-200',
    danger: 'border-red-800 bg-red-950 text-red-200',
  }
  return <span className={cn('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium', map[variant])}>{children}</span>
}
