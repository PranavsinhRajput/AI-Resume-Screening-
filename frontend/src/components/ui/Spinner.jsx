import clsx from 'clsx'
import { Loader2 } from 'lucide-react'

export default function Spinner({ className, label }) {
  return (
    <span className="inline-flex items-center gap-2" role={label ? 'status' : undefined}>
      <Loader2 className={clsx('animate-spin', className || 'h-5 w-5')} aria-hidden="true" />
      {label && <span className="text-sm text-muted">{label}</span>}
    </span>
  )
}
