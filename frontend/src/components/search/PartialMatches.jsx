import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import ResultCard from './ResultCard.jsx'

/** @param {{results: import('../../lib/types').SearchResult[], onDetails: (id: string) => void}} props */
export default function PartialMatches({ results, onDetails }) {
  const [open, setOpen] = useState(false)
  if (!results.length) return null
  const Icon = open ? ChevronDown : ChevronRight
  return (
    <section className="space-y-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex min-h-11 w-full items-center gap-2 rounded-xl border border-line bg-elevated px-4 text-left text-sm font-semibold text-text"
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
        Partial matches ({results.length})
        <span className="ml-1 font-normal text-muted">— don't meet every required criterion</span>
      </button>
      {open && (
        <ul className="space-y-3">
          {results.map((r) => (
            <ResultCard key={r.resume_id} result={r} onDetails={onDetails} />
          ))}
        </ul>
      )}
    </section>
  )
}
