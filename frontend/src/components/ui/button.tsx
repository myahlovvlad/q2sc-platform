import * as React from 'react'
import { cn } from '../../lib/utils'

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default' | 'secondary' | 'ghost' | 'danger' }

export function Button({ className, variant = 'default', ...props }: ButtonProps) {
  const variants = {
    default: 'bg-slate-100 text-slate-950 hover:bg-white',
    secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700',
    ghost: 'bg-transparent text-slate-300 hover:bg-slate-800',
    danger: 'bg-red-900 text-red-50 hover:bg-red-800',
  }
  return <button className={cn('inline-flex h-9 items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition disabled:opacity-50', variants[variant], className)} {...props} />
}
