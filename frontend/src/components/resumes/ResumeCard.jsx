import { formatDate, formatExperience } from '../../lib/format.js'
import { ChipList } from '../ui/Chip.jsx'
import ResumeActions from './ResumeActions.jsx'
import StatusBadge from './StatusBadge.jsx'

/**
 * Stacked card for widths below md.
 * @param {{resume: import('../../lib/types').ResumeSummary, onOpen: (id: string) => void}} props
 */
export default function ResumeCard({ resume: r, onOpen }) {
  return (
    <li className="rounded-2xl border border-line bg-panel p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <button
          type="button"
          onClick={() => onOpen(r.id)}
          className="min-h-11 min-w-0 flex-1 text-left"
        >
          <p className="truncate font-semibold text-text">{r.candidate_name || r.original_filename}</p>
          {r.candidate_name && <p className="truncate text-xs text-muted">{r.original_filename}</p>}
        </button>
        <StatusBadge status={r.status} />
      </div>
      {r.status === 'failed' && r.error_message && (
        <p className="mt-2 text-sm text-red-700 dark:text-red-300">{r.error_message}</p>
      )}
      <p className="mt-2 text-sm text-text">
        {r.status === 'done' ? formatExperience(r.total_experience_months) : ''}
        {r.location ? ` · ${r.location}` : ''}
      </p>
      <div className="mt-2">
        <ChipList items={r.skills} max={5} />
      </div>
      <p className="mt-2 text-xs text-muted">Uploaded {formatDate(r.created_at)}</p>
      <div className="mt-3">
        <ResumeActions resume={r} />
      </div>
    </li>
  )
}
