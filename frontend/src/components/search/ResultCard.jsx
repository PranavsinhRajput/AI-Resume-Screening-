import { useState } from 'react'
import clsx from 'clsx'
import { ExternalLink, FileText } from 'lucide-react'
import { openResumePdf } from '../../lib/api.js'
import { useViewAs } from '../../context/ViewAsContext.jsx'
import { formatExperience } from '../../lib/format.js'
import Button from '../ui/Button.jsx'
import { ChipList } from '../ui/Chip.jsx'
import CriteriaList from './CriteriaList.jsx'

/**
 * @param {{result: import('../../lib/types').SearchResult, onDetails: (id: string) => void}} props
 */
export default function ResultCard({ result: r, onDetails }) {
  const { viewAsId } = useViewAs()
  const [error, setError] = useState('')
  const [showSnippets, setShowSnippets] = useState(false)

  const open = async () => {
    setError('')
    try {
      await openResumePdf(r.resume_id, viewAsId)
    } catch (err) {
      setError(err?.message || 'Could not open the PDF.')
    }
  }

  return (
    <li
      className={clsx(
        'rounded-2xl border bg-panel p-4 shadow-soft sm:p-5',
        r.meets_all_required ? 'border-line' : 'border-dashed border-line',
      )}
    >
      <div className="flex items-start gap-3">
        <span className="inline-flex h-8 min-w-8 shrink-0 items-center justify-center rounded-full bg-soft-accent px-2 text-sm font-semibold text-text">
          #{r.rank}
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-base font-semibold text-text">{r.candidate_name || r.original_filename}</h3>
          <p className="text-sm text-muted">
            {formatExperience(r.total_experience_months)}
            {r.location ? ` · ${r.location}` : ''}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-xs uppercase tracking-wide text-muted">Match</p>
          <p className="text-xl font-bold text-accent-strong">{r.match_score}</p>
        </div>
      </div>

      <div className="mt-3">
        <ChipList items={r.skills} max={5} />
      </div>

      <p className="mt-3 text-sm text-text">
        <span className="font-medium">Reason: </span>
        {r.reason}
      </p>

      {r.criteria.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Criteria</p>
          <CriteriaList criteria={r.criteria} />
        </div>
      )}

      {r.snippets.length > 0 && (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowSnippets((v) => !v)}
            aria-expanded={showSnippets}
            className="min-h-11 text-sm font-medium text-accent-strong hover:underline md:min-h-0"
          >
            {showSnippets ? 'Hide matching excerpts' : 'Show matching excerpts'}
          </button>
          {showSnippets && (
            <ul className="mt-2 space-y-2">
              {r.snippets.map((s, i) => (
                <li key={i} className="rounded-lg bg-elevated p-2 text-xs text-muted">
                  <span className="font-semibold capitalize text-text">{s.section}: </span>
                  {s.text}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button variant="primary" size="sm" onClick={open}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          View resume
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onDetails(r.resume_id)}>
          <FileText className="h-4 w-4" aria-hidden="true" />
          Details
        </Button>
      </div>
      {error && (
        <p role="alert" className="mt-2 text-xs text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
    </li>
  )
}
