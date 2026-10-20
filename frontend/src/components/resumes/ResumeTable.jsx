import { formatDate, formatExperience } from '../../lib/format.js'
import { ChipList } from '../ui/Chip.jsx'
import ResumeActions from './ResumeActions.jsx'
import StatusBadge from './StatusBadge.jsx'

/**
 * md+ table view.
 * @param {{items: import('../../lib/types').ResumeSummary[], onOpen: (id: string) => void}} props
 */
export default function ResumeTable({ items, onOpen }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-panel shadow-soft">
      <table className="w-full table-fixed text-left text-sm">
        <thead className="border-b border-line bg-elevated text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="w-[24%] px-4 py-3 font-medium">Candidate</th>
            <th scope="col" className="w-[12%] px-4 py-3 font-medium">Status</th>
            <th scope="col" className="w-[13%] px-4 py-3 font-medium">Experience</th>
            <th scope="col" className="px-4 py-3 font-medium">Top skills</th>
            <th scope="col" className="hidden w-[14%] px-4 py-3 font-medium lg:table-cell">Uploaded</th>
            <th scope="col" className="w-[17%] px-4 py-3 font-medium">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr
              key={r.id}
              className="cursor-pointer border-b border-line last:border-b-0 hover:bg-elevated"
              onClick={() => onOpen(r.id)}
            >
              <td className="px-4 py-3">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onOpen(r.id)
                  }}
                  className="block w-full truncate text-left font-medium text-text hover:underline"
                  title={r.candidate_name || r.original_filename}
                >
                  {r.candidate_name || r.original_filename}
                </button>
                {r.candidate_name && <p className="truncate text-xs text-muted">{r.original_filename}</p>}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={r.status} />
                {r.status === 'failed' && r.error_message && (
                  <p className="mt-1 line-clamp-2 text-xs text-red-700 dark:text-red-300">{r.error_message}</p>
                )}
              </td>
              <td className="px-4 py-3 text-text">
                {r.status === 'done' ? formatExperience(r.total_experience_months) : '—'}
              </td>
              <td className="px-4 py-3">
                <ChipList items={r.skills} max={4} />
              </td>
              <td className="hidden px-4 py-3 text-xs text-muted lg:table-cell">{formatDate(r.created_at)}</td>
              <td className="px-4 py-3">
                <ResumeActions resume={r} compact />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
