import clsx from 'clsx'

export default function Chip({ children, className, title }) {
  return (
    <span
      title={title}
      className={clsx(
        'inline-flex max-w-full items-center truncate rounded-full bg-soft-accent px-2.5 py-0.5 text-xs font-medium text-text',
        className,
      )}
    >
      {children}
    </span>
  )
}

/**
 * Wrapping list of chips with a "+N" overflow chip.
 * @param {{items: string[], max?: number}} props
 */
export function ChipList({ items, max = 6 }) {
  if (!items?.length) return null
  const shown = items.slice(0, max)
  const extra = items.length - shown.length
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <Chip key={s}>{s}</Chip>
      ))}
      {extra > 0 && <Chip title={items.slice(max).join(', ')}>+{extra}</Chip>}
    </div>
  )
}
