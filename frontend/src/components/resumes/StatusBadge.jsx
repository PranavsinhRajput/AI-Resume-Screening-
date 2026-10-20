import clsx from 'clsx'
import { Loader2 } from 'lucide-react'

const STYLES = {
  pending: 'bg-soft-accent text-text',
  processing: 'bg-soft-accent text-text',
  done: 'bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200',
}

const LABELS = { pending: 'Queued', processing: 'Processing…', done: 'Ready', failed: 'Failed' }

/** @param {{status: import('../../lib/types').ResumeStatus}} props */
export default function StatusBadge({ status }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium',
        STYLES[status],
      )}
    >
      {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />}
      {LABELS[status] || status}
    </span>
  )
}
