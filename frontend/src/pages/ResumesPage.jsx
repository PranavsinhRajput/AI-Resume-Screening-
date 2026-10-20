import { useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { FileText, SearchX } from 'lucide-react'
import AppBar from '../components/layout/AppBar.jsx'
import LibraryUsage from '../components/resumes/LibraryUsage.jsx'
import ResumeCard from '../components/resumes/ResumeCard.jsx'
import ResumeDetailDrawer from '../components/resumes/ResumeDetailDrawer.jsx'
import ResumeTable from '../components/resumes/ResumeTable.jsx'
import UploadDropzone from '../components/resumes/UploadDropzone.jsx'
import InterpretationBanner from '../components/search/InterpretationBanner.jsx'
import PartialMatches from '../components/search/PartialMatches.jsx'
import ResultCard from '../components/search/ResultCard.jsx'
import SearchBox from '../components/search/SearchBox.jsx'
import Button from '../components/ui/Button.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import ErrorState from '../components/ui/ErrorState.jsx'
import { SkeletonList } from '../components/ui/Skeleton.jsx'
import { PAGE_SIZE, useResumeList, useResumeStats } from '../hooks/useResumes.js'
import { useSearch } from '../hooks/useSearch.js'
import { useViewAs } from '../context/ViewAsContext.jsx'
import AdminViewBanner from '../components/layout/AdminViewBanner.jsx'

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'done', label: 'Ready' },
  { value: 'processing', label: 'Processing' },
  { value: 'pending', label: 'Queued' },
  { value: 'failed', label: 'Failed' },
]

function ResumesTab({ stats, onOpen }) {
  const { readOnly } = useViewAs()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const list = useResumeList({ status: status || undefined, page }, stats)
  const data = list.data
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1

  return (
    <div className="space-y-5">
      <LibraryUsage total={stats.total} limit={stats.limit} />
      {!readOnly && <UploadDropzone stats={stats} />}

      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Filter by status">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            aria-pressed={status === f.value}
            onClick={() => {
              setStatus(f.value)
              setPage(1)
            }}
            className={clsx(
              'min-h-11 rounded-full border px-3 text-sm md:min-h-9',
              status === f.value
                ? 'border-accent bg-soft-accent font-semibold text-text'
                : 'border-line bg-panel text-muted hover:text-text',
            )}
          >
            {f.label}
            {f.value && stats[f.value] > 0 ? ` (${stats[f.value]})` : ''}
          </button>
        ))}
      </div>

      <div aria-live="polite">
        {list.isLoading && <SkeletonList rows={5} />}
        {list.error && !data && <ErrorState error={list.error} onRetry={list.refetch} />}
        {data && data.items.length === 0 && (
          <EmptyState
            icon={FileText}
            title={
              status ? 'No resumes with this status.' : readOnly ? 'This user has no resumes yet.' : 'No resumes yet — drag PDFs here'
            }
          >
            {!status && !readOnly && 'Upload PDF resumes above. They are parsed in the background and become searchable.'}
          </EmptyState>
        )}
        {data && data.items.length > 0 && (
          <>
            <div className="hidden md:block">
              <ResumeTable items={data.items} onOpen={onOpen} />
            </div>
            <ul className="space-y-3 md:hidden">
              {data.items.map((r) => (
                <ResumeCard key={r.id} resume={r} onOpen={onOpen} />
              ))}
            </ul>
            {totalPages > 1 && (
              <nav className="mt-4 flex items-center justify-between gap-2" aria-label="Pagination">
                <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <span className="text-sm text-muted">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function SearchTab({ stats, onOpen, search }) {
  const { readOnly } = useViewAs()
  const response = search.data

  if (stats.done === 0) {
    return (
      <EmptyState icon={SearchX} title={readOnly ? 'This user has no processed resumes yet.' : 'Upload and process resumes first.'}>
        {stats.pending + stats.processing > 0
          ? 'Resumes are being processed. Search becomes available as soon as one is ready.'
          : readOnly
            ? null
            : 'Go to the Resumes tab to upload PDFs.'}
      </EmptyState>
    )
  }

  const full = response ? response.results.filter((r) => r.meets_all_required) : []
  const partial = response ? response.results.filter((r) => !r.meets_all_required) : []

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="rounded-2xl border border-line bg-panel p-4 shadow-soft sm:p-5">
        <SearchBox loading={search.isPending} onSearch={(q) => search.mutate({ query: q })} />
      </div>

      {search.error && (
        <ErrorState error={search.error} onRetry={() => search.variables && search.mutate(search.variables)} />
      )}

      {response && !search.isPending && (
        <div className="space-y-4">
          <InterpretationBanner response={response} />
          {response.results.length === 0 ? (
            <EmptyState icon={SearchX} title="No matching resumes found.">
              Try a broader request or different skills.
            </EmptyState>
          ) : (
            <>
              <p className="text-sm text-muted">
                {full.length} result{full.length === 1 ? '' : 's'} · {response.candidates_considered} candidates
                considered
              </p>
              {full.length > 0 && (
                <ul className="space-y-3">
                  {full.map((r) => (
                    <ResultCard key={r.resume_id} result={r} onDetails={onOpen} />
                  ))}
                </ul>
              )}
              <PartialMatches results={partial} onDetails={onOpen} />
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function ResumesPage() {
  const [params, setParams] = useSearchParams()
  const { viewAsId } = useViewAs()
  const stats = useResumeStats()
  // Lives at page level so results survive switching tabs.
  const search = useSearch()
  const [openId, setOpenId] = useState(/** @type {string|null} */ (null))
  const closeDrawer = useCallback(() => setOpenId(null), [])

  const tabParam = params.get('tab')
  const tab =
    tabParam === 'resumes' || tabParam === 'search' ? tabParam : stats.data?.total ? 'search' : 'resumes'

  const setTab = (t) => {
    const next = new URLSearchParams(params)
    next.set('tab', t)
    setParams(next, { replace: true })
  }

  return (
    <div className="min-h-screen bg-app">
      {viewAsId ? (
        <div className="sticky top-0 z-40">
          <AdminViewBanner />
          <AppBar />
        </div>
      ) : (
        <AppBar />
      )}
      <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6 sm:py-8">
        <div role="tablist" aria-label="Library" className="mb-6 flex gap-1 border-b border-line">
          {[
            { id: 'resumes', label: 'Resumes' },
            { id: 'search', label: 'Search' },
          ].map((t) => (
            <button
              key={t.id}
              role="tab"
              type="button"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={clsx(
                '-mb-px min-h-11 rounded-t-xl border-b-2 px-4 text-sm font-medium',
                tab === t.id
                  ? 'border-accent bg-soft-accent text-text'
                  : 'border-transparent text-muted hover:text-text',
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
          {stats.isLoading && <SkeletonList rows={4} />}
          {stats.error && !stats.data && <ErrorState error={stats.error} onRetry={stats.refetch} />}
          {stats.data &&
            (tab === 'resumes' ? (
              <ResumesTab stats={stats.data} onOpen={setOpenId} />
            ) : (
              <SearchTab stats={stats.data} onOpen={setOpenId} search={search} />
            ))}
        </div>
      </main>
      <ResumeDetailDrawer resumeId={openId} onClose={closeDrawer} />
    </div>
  )
}
