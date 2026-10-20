import { useState } from 'react'
import clsx from 'clsx'
import { Check, HelpCircle, X } from 'lucide-react'

function Evidence({ text }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  const long = text.length > 160
  return (
    <div className="mt-1">
      <p className={clsx('rounded-lg bg-elevated px-2 py-1 text-xs italic text-muted', !open && 'line-clamp-3')}>
        “{text}”
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="text-xs font-medium text-accent-strong hover:underline"
        >
          {open ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

const ICONS = {
  true: { Icon: Check, cls: 'text-green-700 dark:text-green-300', label: 'met' },
  false: { Icon: X, cls: 'text-red-700 dark:text-red-300', label: 'not met' },
  null: { Icon: HelpCircle, cls: 'text-muted', label: 'unknown' },
}

/** @param {{criteria: import('../../lib/types').SearchResult['criteria']}} props */
export default function CriteriaList({ criteria }) {
  if (!criteria?.length) return null
  return (
    <ul className="space-y-1.5" aria-label="Criteria">
      {criteria.map((c, i) => {
        const { Icon, cls, label } = ICONS[String(c.met)] || ICONS.null
        return (
          <li key={i} className="text-sm">
            <div className="flex items-start gap-1.5">
              <Icon className={clsx('mt-0.5 h-4 w-4 shrink-0', cls)} aria-hidden="true" />
              <span className="min-w-0 text-text">
                <span className="sr-only">{label}: </span>
                {c.criterion}
                {!c.required && <span className="text-muted"> (nice to have)</span>}
              </span>
            </div>
            {c.met === true && <Evidence text={c.evidence} />}
          </li>
        )
      })}
    </ul>
  )
}
