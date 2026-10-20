import clsx from 'clsx'

export default function Skeleton({ className }) {
  return (
    <div
      aria-hidden="true"
      className={clsx('rounded-lg bg-soft-accent', className)}
      style={{ animation: 'skeleton-pulse 1.5s ease-in-out infinite' }}
    />
  )
}

export function SkeletonList({ rows = 5 }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  )
}
