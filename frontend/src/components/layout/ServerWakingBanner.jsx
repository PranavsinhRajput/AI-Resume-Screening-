import { useServerWakeup } from '../../hooks/useServerWakeup.js'
import Spinner from '../ui/Spinner.jsx'

export default function ServerWakingBanner() {
  const { showBanner, failed } = useServerWakeup()

  if (!showBanner && !failed) return <div aria-live="polite" className="sr-only" />

  return (
    <div
      aria-live="polite"
      role="status"
      className="sticky top-0 z-40 flex items-center justify-center gap-2 border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
    >
      {failed ? (
        <span>The server is not responding. Please refresh the page in a moment.</span>
      ) : (
        <>
          <Spinner className="h-4 w-4" />
          <span>Starting the server — this can take up to a minute on free hosting…</span>
        </>
      )}
    </div>
  )
}
