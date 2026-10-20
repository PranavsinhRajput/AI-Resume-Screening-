import { AlertTriangle } from 'lucide-react'
import Button from './Button.jsx'

export default function ErrorState({ error, onRetry }) {
  const message = error?.message || 'Something went wrong. Please try again.'
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-2xl border border-red-300 bg-red-50 p-4 text-red-800 sm:flex-row sm:items-center dark:border-red-800 dark:bg-red-950 dark:text-red-200"
    >
      <AlertTriangle className="h-5 w-5 shrink-0" aria-hidden="true" />
      <p className="flex-1 text-sm">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  )
}
