import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Hourglass, LogOut, ShieldX } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import Button from '../components/ui/Button.jsx'
import AuthLayout from './AuthLayout.jsx'

/**
 * Shown to signed-in users whose account isn't approved yet (or was rejected).
 * @param {{status?: 'pending'|'rejected'|'approved', onCheckAgain: () => void, checking: boolean}} props
 */
export default function PendingApprovalPage({ status, onCheckAgain, checking }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const rejected = status === 'rejected'

  const logout = async () => {
    await signOut()
    qc.clear()
    navigate('/login', { replace: true })
  }

  return (
    <AuthLayout title={rejected ? 'Access not approved' : 'Waiting for approval'}>
      <div role="status" aria-live="polite" className="flex items-start gap-3 text-sm text-text">
        {rejected ? (
          <ShieldX className="h-6 w-6 shrink-0 text-red-600 dark:text-red-400" aria-hidden="true" />
        ) : (
          <Hourglass className="h-6 w-6 shrink-0 text-accent" aria-hidden="true" />
        )}
        <div className="space-y-2">
          {rejected ? (
            <p>Your account request was not approved. Contact the administrator if you think this is a mistake.</p>
          ) : (
            <>
              <p>Your account has been created and is waiting for an administrator to approve it.</p>
              <p className="text-muted">
                This page checks automatically every few seconds — you'll get in as soon as you're approved.
              </p>
            </>
          )}
          <p className="break-all text-xs text-muted">Signed in as {user?.email}</p>
        </div>
      </div>
      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        {!rejected && (
          <Button onClick={onCheckAgain} loading={checking} className="justify-center">
            Check again
          </Button>
        )}
        <Button variant="secondary" onClick={logout} className="justify-center">
          <LogOut className="h-4 w-4" aria-hidden="true" />
          Log out
        </Button>
      </div>
    </AuthLayout>
  )
}
