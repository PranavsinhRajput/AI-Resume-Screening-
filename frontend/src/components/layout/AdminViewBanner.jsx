import { Link } from 'react-router-dom'
import { Eye, X } from 'lucide-react'
import { useViewAs } from '../../context/ViewAsContext.jsx'

/** Sticky strip shown at the very top while an admin is viewing another user's library. */
export default function AdminViewBanner() {
  const { viewAsId, viewAsEmail } = useViewAs()
  if (!viewAsId) return null
  return (
    <div
      role="status"
      className="sticky top-0 z-40 border-b border-accent-strong bg-accent text-harvest-orange-950"
    >
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-3 gap-y-1 px-4 py-2 sm:px-6">
        <Eye className="h-4 w-4 shrink-0" aria-hidden="true" />
        <p className="min-w-0 flex-1 text-sm">
          <span className="font-bold uppercase tracking-wide">Viewing as admin</span>
          <span className="break-all"> — {viewAsEmail || 'user'}</span>
          <span className="hidden sm:inline"> · read-only</span>
        </p>
        <Link
          to="/admin?tab=approved"
          className="inline-flex min-h-11 items-center gap-1 rounded-lg px-2 text-sm font-semibold underline-offset-2 hover:underline md:min-h-8"
        >
          <X className="h-4 w-4" aria-hidden="true" />
          Exit
        </Link>
      </div>
    </div>
  )
}
