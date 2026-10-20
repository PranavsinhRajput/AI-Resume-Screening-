import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { useMe } from '../../hooks/useMe.js'
import PendingApprovalPage from '../../pages/PendingApprovalPage.jsx'
import ErrorState from '../ui/ErrorState.jsx'
import Spinner from '../ui/Spinner.jsx'

function FullScreen({ children }) {
  return <div className="flex min-h-screen items-center justify-center bg-app px-4">{children}</div>
}

/**
 * Requires a session AND an approved account. `requireAdmin` additionally requires the admin role.
 */
export default function ProtectedRoute({ children, requireAdmin = false }) {
  const { session, loading } = useAuth()
  const location = useLocation()
  const me = useMe()

  if (loading) {
    return (
      <FullScreen>
        <Spinner label="Loading…" />
      </FullScreen>
    )
  }
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  if (me.isLoading) {
    return (
      <FullScreen>
        <Spinner label="Checking your access…" />
      </FullScreen>
    )
  }
  if (me.error) {
    return (
      <FullScreen>
        <div className="w-full max-w-md">
          <ErrorState error={me.error} onRetry={me.refetch} />
        </div>
      </FullScreen>
    )
  }
  if (me.data?.status !== 'approved') {
    return <PendingApprovalPage status={me.data?.status} onCheckAgain={me.refetch} checking={me.isFetching} />
  }
  if (requireAdmin && me.data.role !== 'admin') {
    return <Navigate to="/resumes" replace />
  }
  return children
}
