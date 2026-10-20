import { useEffect, useId, useRef, useState } from 'react'
import { ExternalLink, X } from 'lucide-react'
import { useResumeDetail } from '../../hooks/useResumes.js'
import { formatExperience, formatYearMonth } from '../../lib/format.js'
import { ChipList } from '../ui/Chip.jsx'
import ErrorState from '../ui/ErrorState.jsx'
import { SkeletonList } from '../ui/Skeleton.jsx'
import ResumeActions from './ResumeActions.jsx'
import StatusBadge from './StatusBadge.jsx'

function ShowMore({ text, limit = 280 }) {
  const [open, setOpen] = useState(false)
  if (!text) return null
  if (text.length <= limit) return <p className="whitespace-pre-line text-sm text-text">{text}</p>
  return (
    <div>
      <p className="whitespace-pre-line text-sm text-text">{open ? text : text.slice(0, limit).trimEnd() + '…'}</p>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-1 min-h-11 text-sm font-medium text-accent-strong hover:underline md:min-h-0"
      >
        {open ? 'Show less' : 'Show more'}
      </button>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <section className="space-y-2 border-t border-line pt-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</h3>
      {children}
    </section>
  )
}

function SafeLink({ href, label }) {
  if (!href) return null
  const url = /^https?:\/\//i.test(href) ? href : `https://${href}`
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 break-all text-sm text-accent-strong hover:underline"
    >
      {label} <ExternalLink className="h-3 w-3" aria-hidden="true" />
    </a>
  )
}

/**
 * Right-side drawer on lg+, full-screen sheet below lg.
 * @param {{resumeId: string|null, onClose: () => void}} props
 */
export default function ResumeDetailDrawer({ resumeId, onClose }) {
  const titleId = useId()
  const closeRef = useRef(null)
  const { data: r, isLoading, error, refetch } = useResumeDetail(resumeId)

  useEffect(() => {
    if (!resumeId) return
    closeRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [resumeId, onClose])

  if (!resumeId) return null

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 hidden bg-black/40 lg:block" onClick={onClose} aria-hidden="true" />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="absolute inset-0 flex flex-col bg-sidebar shadow-soft lg:inset-y-0 lg:left-auto lg:right-0 lg:w-[36rem] lg:border-l lg:border-line"
      >
        <div className="flex items-center gap-3 border-b border-line px-4 py-3 sm:px-6">
          <h2 id={titleId} className="min-w-0 flex-1 truncate text-lg font-semibold text-text">
            {r ? r.candidate_name || r.original_filename : 'Resume details'}
          </h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close details"
            className="inline-flex h-11 w-11 items-center justify-center rounded-xl text-text hover:bg-elevated"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-6">
          {isLoading && <SkeletonList rows={6} />}
          {error && <ErrorState error={error} onRetry={refetch} />}
          {r && (
            <>
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge status={r.status} />
                  {r.status === 'done' && (
                    <span className="text-sm text-text">{formatExperience(r.total_experience_months)}</span>
                  )}
                </div>
                {r.headline && <p className="text-sm font-medium text-text">{r.headline}</p>}
                {r.status === 'failed' && r.error_message && (
                  <p className="text-sm text-red-700 dark:text-red-300">{r.error_message}</p>
                )}
                <dl className="grid grid-cols-1 gap-1 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-4">
                  {r.email && (
                    <>
                      <dt className="text-muted">Email</dt>
                      <dd className="break-all text-text">{r.email}</dd>
                    </>
                  )}
                  {r.phone && (
                    <>
                      <dt className="text-muted">Phone</dt>
                      <dd className="text-text">{r.phone}</dd>
                    </>
                  )}
                  {r.location && (
                    <>
                      <dt className="text-muted">Location</dt>
                      <dd className="text-text">{r.location}</dd>
                    </>
                  )}
                  <dt className="text-muted">File</dt>
                  <dd className="break-all text-text">{r.original_filename}</dd>
                </dl>
                <div className="flex flex-wrap gap-3">
                  <SafeLink href={r.links?.linkedin} label="LinkedIn" />
                  <SafeLink href={r.links?.github} label="GitHub" />
                  <SafeLink href={r.links?.portfolio} label="Portfolio" />
                </div>
                <ResumeActions resume={r} onDeleted={onClose} />
              </div>

              {r.summary && (
                <Section title="Summary">
                  <ShowMore text={r.summary} />
                </Section>
              )}

              {r.skills?.length > 0 && (
                <Section title="Skills">
                  <ChipList items={r.skills} max={40} />
                </Section>
              )}

              {r.experiences?.length > 0 && (
                <Section title="Experience">
                  <ol className="space-y-4">
                    {r.experiences.map((e, i) => (
                      <li key={i} className="space-y-1">
                        <p className="text-sm font-semibold text-text">
                          {[e.title, e.company].filter(Boolean).join(' · ') || 'Role'}
                        </p>
                        <p className="text-xs text-muted">
                          {formatYearMonth(e.start_date) || '?'} –{' '}
                          {e.is_current ? 'Present' : formatYearMonth(e.end_date) || '?'}
                          {e.employment_type && e.employment_type !== 'unknown'
                            ? ` · ${e.employment_type.replace('_', ' ')}`
                            : ''}
                          {e.location ? ` · ${e.location}` : ''}
                        </p>
                        <ShowMore text={e.description} limit={200} />
                      </li>
                    ))}
                  </ol>
                </Section>
              )}

              {r.projects?.length > 0 && (
                <Section title="Projects">
                  <ul className="space-y-3">
                    {r.projects.map((p, i) => (
                      <li key={i} className="space-y-1">
                        <p className="text-sm font-semibold text-text">{p.name}</p>
                        <ShowMore text={p.description} limit={200} />
                        <ChipList items={p.technologies} max={8} />
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {r.education?.length > 0 && (
                <Section title="Education">
                  <ul className="space-y-2">
                    {r.education.map((ed, i) => (
                      <li key={i} className="text-sm text-text">
                        <p className="font-medium">
                          {[ed.degree, ed.field_of_study].filter(Boolean).join(' in ') || 'Education'}
                        </p>
                        <p className="text-xs text-muted">
                          {[ed.institution, [ed.start_year, ed.end_year].filter(Boolean).join('–'), ed.grade]
                            .filter(Boolean)
                            .join(' · ')}
                        </p>
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {r.certifications?.length > 0 && (
                <Section title="Certifications">
                  <ul className="list-disc space-y-1 pl-5 text-sm text-text">
                    {r.certifications.map((c, i) => (
                      <li key={i}>{c}</li>
                    ))}
                  </ul>
                </Section>
              )}

              {r.parse_warnings?.length > 0 && (
                <Section title="Parse warnings">
                  <ul className="space-y-1 text-sm text-amber-800 dark:text-amber-200">
                    {r.parse_warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </Section>
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
