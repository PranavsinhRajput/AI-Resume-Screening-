import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ChevronDown, FileSearch, LogOut, ShieldCheck } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../context/AuthContext.jsx'
import { useMe } from '../../hooks/useMe.js'
import ThemeToggle from './ThemeToggle.jsx'

export default function AppBar() {
  const { user, signOut } = useAuth()
  const me = useMe()
  const isAdmin = me.data?.role === 'admin'
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  const logout = async () => {
    setOpen(false)
    await signOut()
    qc.clear()
    navigate('/login', { replace: true })
  }

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-sidebar">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6">
        <Link to="/resumes" className="flex min-w-0 items-center gap-2 font-semibold text-text">
          <FileSearch className="h-6 w-6 shrink-0 text-accent" aria-hidden="true" />
          <span className="truncate">Resume Screening AI</span>
        </Link>
        <div className="ml-auto flex items-center gap-2">
          {isAdmin && (
            <Link
              to="/admin"
              className="hidden h-11 items-center gap-1.5 rounded-xl border border-line bg-panel px-3 text-sm font-medium text-text hover:bg-elevated sm:inline-flex"
            >
              <ShieldCheck className="h-4 w-4 text-accent" aria-hidden="true" />
              Admin panel
            </Link>
          )}
          <ThemeToggle />
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              aria-haspopup="menu"
              aria-expanded={open}
              aria-label="Account menu"
              className="inline-flex h-11 max-w-[11rem] items-center gap-1 rounded-xl border border-line bg-panel px-3 text-sm text-text hover:bg-elevated sm:max-w-xs"
            >
              <span className="truncate">{user?.email}</span>
              <ChevronDown className="h-4 w-4 shrink-0" aria-hidden="true" />
            </button>
            {open && (
              <div
                role="menu"
                className="absolute right-0 mt-2 w-56 rounded-xl border border-line bg-panel p-1 shadow-soft"
              >
                <p className="truncate px-3 py-2 text-xs text-muted">{user?.email}</p>
                <Link
                  to="/resumes"
                  role="menuitem"
                  onClick={() => setOpen(false)}
                  className="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm text-text hover:bg-elevated"
                >
                  <FileSearch className="h-4 w-4" aria-hidden="true" />
                  My library
                </Link>
                {isAdmin && (
                  <Link
                    to="/admin"
                    role="menuitem"
                    onClick={() => setOpen(false)}
                    className="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm text-text hover:bg-elevated"
                  >
                    <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                    Admin panel
                  </Link>
                )}
                <button
                  type="button"
                  role="menuitem"
                  onClick={logout}
                  className="flex min-h-11 w-full items-center gap-2 rounded-lg px-3 text-sm text-text hover:bg-elevated"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" />
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
