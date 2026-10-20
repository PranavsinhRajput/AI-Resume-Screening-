import clsx from 'clsx'

/**
 * "N / limit resumes" with a thin progress bar. Warning style at ≥ 90 %.
 * @param {{total: number, limit: number, className?: string}} props
 */
export default function LibraryUsage({ total, limit, className }) {
  const pct = limit > 0 ? Math.min(100, (total / limit) * 100) : 0
  const warn = pct >= 90
  return (
    <div className={clsx('space-y-1.5', className)}>
      <p
        className={clsx(
          'text-sm font-medium',
          warn ? 'text-amber-700 dark:text-amber-300' : 'text-muted',
        )}
      >
        {total} / {limit} resumes
      </p>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-soft-accent"
        role="progressbar"
        aria-label="Library usage"
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={total}
      >
        <div className="h-full rounded-full bg-accent transition-[width]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
