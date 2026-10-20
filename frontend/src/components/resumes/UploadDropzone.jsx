import { useRef, useState } from 'react'
import clsx from 'clsx'
import { CheckCircle2, UploadCloud, XCircle } from 'lucide-react'
import { useUploadResumes } from '../../hooks/useResumes.js'
import {
  MAX_FILE_BYTES,
  MAX_FILE_MB,
  MAX_FILES_PER_UPLOAD,
  MAX_PAGES,
  libraryFullMessage,
  reasonMessages,
} from '../../lib/config.js'
import Button from '../ui/Button.jsx'
import LibraryUsage from './LibraryUsage.jsx'

/**
 * Client-side pre-check (the server stays the authority).
 * @param {File[]} files
 * @param {number} freeSlots
 */
function precheck(files, freeSlots) {
  const send = []
  const rejected = []
  for (const f of files) {
    if (f.size > MAX_FILE_BYTES) rejected.push({ filename: f.name, reason: 'file_too_large' })
    else send.push(f)
  }
  const overLimit = send.splice(MAX_FILES_PER_UPLOAD)
  for (const f of overLimit) rejected.push({ filename: f.name, reason: 'too_many_files' })
  const overSlots = send.splice(Math.max(0, freeSlots))
  for (const f of overSlots) rejected.push({ filename: f.name, reason: 'library_full' })
  return { send, rejected }
}

/** @param {{stats: import('../../lib/types').ResumeStats}} props */
export default function UploadDropzone({ stats }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const [pending, setPending] = useState(/** @type {string[]} */ ([]))
  const [results, setResults] = useState(null)
  const upload = useUploadResumes()

  const limit = stats.limit
  const freeSlots = Math.max(0, limit - stats.total)
  const full = stats.total >= limit
  const messages = reasonMessages(limit)

  const handleFiles = (fileList) => {
    if (full || upload.isPending) return
    const files = Array.from(fileList || [])
    if (!files.length) return
    const { send, rejected } = precheck(files, freeSlots)
    const clientRejected = rejected.map((r) => ({ ...r, message: messages[r.reason] }))
    if (!send.length) {
      setResults({ accepted: [], rejected: clientRejected })
      return
    }
    setResults(null)
    setPending(send.map((f) => f.name))
    setProgress(0)
    upload.mutate(
      { files: send, onProgress: setProgress },
      {
        onSuccess: (data) =>
          setResults({ accepted: data.accepted, rejected: [...data.rejected, ...clientRejected] }),
        onError: (err) =>
          setResults({ accepted: [], rejected: clientRejected, error: err?.message || 'Upload failed.' }),
        onSettled: () => setPending([]),
      },
    )
  }

  return (
    <section aria-label="Upload resumes" className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          if (!full) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        aria-disabled={full}
        className={clsx(
          'rounded-2xl border-2 border-dashed p-5 transition-colors sm:p-6',
          full
            ? 'cursor-not-allowed border-line bg-elevated opacity-70'
            : dragging
              ? 'border-accent bg-soft-accent'
              : 'border-line bg-panel',
        )}
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <UploadCloud className="h-8 w-8 text-accent" aria-hidden="true" />
          {full ? (
            <p className="text-sm font-medium text-amber-700 dark:text-amber-300">{libraryFullMessage(limit)}</p>
          ) : (
            <>
              <p className="text-sm text-text">
                <span className="font-semibold">Drag PDF resumes here</span> or choose files
              </p>
              <p className="text-xs text-muted">
                PDF only · max {MAX_FILE_MB} MB and {MAX_PAGES} pages each · up to {MAX_FILES_PER_UPLOAD} files at a
                time
              </p>
            </>
          )}
          <Button
            variant="secondary"
            onClick={() => inputRef.current?.click()}
            disabled={full || upload.isPending}
          >
            Choose files
          </Button>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="sr-only"
            aria-label="Choose PDF resumes"
            tabIndex={-1}
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
          <LibraryUsage total={stats.total} limit={limit} className="w-full max-w-xs" />
        </div>
      </div>

      <div aria-live="polite">
        {upload.isPending && (
          <div className="space-y-2 rounded-2xl border border-line bg-panel p-4">
            <p className="text-sm text-text">
              Uploading {pending.length} file{pending.length === 1 ? '' : 's'}… {Math.round(progress * 100)}%
            </p>
            <div className="h-1.5 overflow-hidden rounded-full bg-soft-accent">
              <div className="h-full bg-accent transition-[width]" style={{ width: `${progress * 100}%` }} />
            </div>
            <ul className="space-y-1 text-xs text-muted">
              {pending.map((name, i) => (
                <li key={`${name}-${i}`} className="truncate">
                  {name}
                </li>
              ))}
            </ul>
          </div>
        )}

        {results && (
          <div className="space-y-2 rounded-2xl border border-line bg-panel p-4">
            <div className="flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-text">
                {results.accepted.length} accepted · {results.rejected.length} rejected
              </p>
              <Button variant="ghost" size="sm" onClick={() => setResults(null)}>
                Dismiss
              </Button>
            </div>
            {results.error && <p className="text-sm text-red-700 dark:text-red-300">{results.error}</p>}
            <ul className="space-y-1.5">
              {results.accepted.map((a) => (
                <li key={a.resume_id} className="flex items-start gap-2 text-sm text-text">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600 dark:text-green-400" aria-hidden="true" />
                  <span className="min-w-0 break-words">
                    {a.filename} <span className="text-muted">— queued for processing</span>
                  </span>
                </li>
              ))}
              {results.rejected.map((r, i) => (
                <li key={`${r.filename}-${i}`} className="flex items-start gap-2 text-sm text-text">
                  <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600 dark:text-red-400" aria-hidden="true" />
                  <span className="min-w-0 break-words">
                    {r.filename} <span className="text-muted">— {messages[r.reason] || r.message}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
