import { useState } from 'react'
import { ExternalLink, RotateCw, Trash2 } from 'lucide-react'
import { openResumePdf } from '../../lib/api.js'
import { useDeleteResume, useRetryResume } from '../../hooks/useResumes.js'
import { useViewAs } from '../../context/ViewAsContext.jsx'
import Button from '../ui/Button.jsx'
import Dialog from '../ui/Dialog.jsx'

/**
 * Open PDF / Retry / Delete actions shared by the table, cards and detail drawer.
 * @param {{resume: import('../../lib/types').ResumeSummary, onDeleted?: () => void, compact?: boolean}} props
 */
export default function ResumeActions({ resume, onDeleted, compact = false }) {
  const { viewAsId, readOnly } = useViewAs()
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const del = useDeleteResume()
  const retry = useRetryResume()

  const open = async (e) => {
    e.stopPropagation()
    setError('')
    try {
      await openResumePdf(resume.id, viewAsId)
    } catch (err) {
      setError(err?.message || 'Could not open the PDF.')
    }
  }

  return (
    <div className="flex flex-col gap-1" onClick={(e) => e.stopPropagation()}>
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="secondary" size="sm" onClick={open} aria-label={`Open PDF ${resume.original_filename}`}>
          <ExternalLink className="h-4 w-4" aria-hidden="true" />
          {!compact && 'Open PDF'}
        </Button>
        {!readOnly && resume.status === 'failed' && (
          <Button
            variant="secondary"
            size="sm"
            loading={retry.isPending}
            onClick={() => retry.mutate(resume.id, { onError: (err) => setError(err?.message) })}
            aria-label={`Retry processing ${resume.original_filename}`}
          >
            <RotateCw className="h-4 w-4" aria-hidden="true" />
            {!compact && 'Retry'}
          </Button>
        )}
        {!readOnly && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setConfirming(true)}
            aria-label={`Delete ${resume.original_filename}`}
          >
            <Trash2 className="h-4 w-4 text-red-600 dark:text-red-400" aria-hidden="true" />
            {!compact && 'Delete'}
          </Button>
        )}
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Dialog
        open={confirming}
        title="Delete this resume?"
        confirmLabel="Delete"
        danger
        loading={del.isPending}
        onCancel={() => setConfirming(false)}
        onConfirm={() =>
          del.mutate(resume.id, {
            onSuccess: () => {
              setConfirming(false)
              onDeleted?.()
            },
            onError: (err) => {
              setConfirming(false)
              setError(err?.message || 'Could not delete.')
            },
          })
        }
      >
        Delete this resume? This also removes the PDF.
      </Dialog>
    </div>
  )
}
