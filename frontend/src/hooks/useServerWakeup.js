import { useEffect, useState } from 'react'
import { api, subscribeSlowRequests } from '../lib/api.js'

const SHOW_AFTER_MS = 2500
const RETRY_EVERY_MS = 3000
const GIVE_UP_AFTER_MS = 90000

/**
 * Pings /health on mount. If it hasn't answered within 2.5 s the "waking" banner shows and we keep
 * retrying (90 s overall). Any later request slower than 5 s also turns the banner on.
 */
export function useServerWakeup() {
  const [waking, setWaking] = useState(false)
  const [slow, setSlow] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    let retryTimer = null
    const started = Date.now()
    const showTimer = setTimeout(() => {
      if (!cancelled) setWaking(true)
    }, SHOW_AFTER_MS)

    const attempt = async () => {
      const controller = new AbortController()
      const abortTimer = setTimeout(() => controller.abort(), 15000)
      try {
        await api.health(controller.signal)
        if (cancelled) return
        clearTimeout(showTimer)
        setWaking(false)
        setFailed(false)
      } catch {
        if (cancelled) return
        if (Date.now() - started > GIVE_UP_AFTER_MS) {
          setWaking(false)
          setFailed(true)
          return
        }
        retryTimer = setTimeout(attempt, RETRY_EVERY_MS)
      } finally {
        clearTimeout(abortTimer)
      }
    }
    attempt()

    return () => {
      cancelled = true
      clearTimeout(showTimer)
      clearTimeout(retryTimer)
    }
  }, [])

  useEffect(() => subscribeSlowRequests(setSlow), [])

  return { showBanner: waking || slow, failed }
}
