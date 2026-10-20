import { useCallback, useEffect, useState } from 'react'

/** @typedef {'light'|'dark'} Theme */

/** @returns {Theme} */
function initialTheme() {
  try {
    const stored = localStorage.getItem('theme')
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // storage unavailable
  }
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

/** @param {Theme} theme */
function applyTheme(theme) {
  document.documentElement.dataset.theme = theme
}

export function useTheme() {
  const [theme, setTheme] = useState(initialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  // Keep multiple toggles (and tabs) in sync.
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === 'theme' && (e.newValue === 'light' || e.newValue === 'dark')) setTheme(e.newValue)
    }
    const onLocal = (e) => setTheme(e.detail)
    window.addEventListener('storage', onStorage)
    window.addEventListener('themechange', onLocal)
    return () => {
      window.removeEventListener('storage', onStorage)
      window.removeEventListener('themechange', onLocal)
    }
  }, [])

  const toggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark'
    try {
      localStorage.setItem('theme', next)
    } catch {
      // storage unavailable
    }
    applyTheme(next)
    setTheme(next)
    window.dispatchEvent(new CustomEvent('themechange', { detail: next }))
  }, [theme])

  return { theme, toggle }
}
