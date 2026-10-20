import { useLocation, useParams } from 'react-router-dom'
import { ViewAsProvider } from '../context/ViewAsContext.jsx'
import { useAdminUsers } from '../hooks/useAdmin.js'
import ResumesPage from './ResumesPage.jsx'

/** /admin/users/:userId — the user's Resumes page, read-only, with the "Viewing as admin" banner. */
export default function AdminViewPage() {
  const { userId } = useParams()
  const location = useLocation()
  // Email comes from the admin list navigation; fall back to looking it up (e.g. after a reload).
  const approved = useAdminUsers('approved')
  const email =
    location.state?.email || approved.data?.find((u) => u.id === userId)?.email || null

  return (
    <ViewAsProvider key={userId} userId={userId} email={email}>
      <ResumesPage />
    </ViewAsProvider>
  )
}
