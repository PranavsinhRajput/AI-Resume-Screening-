import { useEffect, useId, useRef } from 'react'
import Button from './Button.jsx'

/**
 * Confirm dialog: centered on md+, full-width bottom sheet on mobile.
 */
export default function Dialog({
  open,
  title,
  children,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  danger = false,
  loading = false,
}) {
  const titleId = useId()
  const cancelRef = useRef(null)

  useEffect(() => {
    if (!open) return
    cancelRef.current?.focus()
    const onKey = (e) => {
      if (e.key === 'Escape') onCancel?.()
    }
    document.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center">
      <div className="absolute inset-0 bg-black/50" onClick={onCancel} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative w-full rounded-t-2xl border border-line bg-panel p-5 shadow-soft md:max-w-md md:rounded-2xl"
      >
        <h2 id={titleId} className="text-lg font-semibold text-text">
          {title}
        </h2>
        {children && <div className="mt-2 text-sm text-muted">{children}</div>}
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Button ref={cancelRef} variant="secondary" onClick={onCancel} className="justify-center">
            {cancelLabel}
          </Button>
          <Button
            variant={danger ? 'danger' : 'primary'}
            onClick={onConfirm}
            loading={loading}
            className="justify-center"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}
