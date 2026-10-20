import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './context/AuthContext.jsx'
import { SESSION_EXPIRED_MESSAGE, setAccessChangedHandler, setUnauthorizedHandler } from './lib/api.js'
import ProtectedRoute from './components/layout/ProtectedRoute.jsx'
import ServerWakingBanner from './components/layout/ServerWakingBanner.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import ResumesPage from './pages/ResumesPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import AdminPage from './pages/AdminPage.jsx'
import AdminViewPage from './pages/AdminViewPage.jsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, error) => error?.status !== 401 && error?.status !== 404 && count < 2,
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
    mutations: { retry: false },
  },
})

function UnauthorizedRedirect() {
  const navigate = useNavigate()
  useEffect(() => {
    setUnauthorizedHandler(() => {
      queryClient.clear()
      navigate('/login', { replace: true, state: { message: SESSION_EXPIRED_MESSAGE } })
    })
    // Access revoked while signed in → re-check /me so the approval screen takes over.
    setAccessChangedHandler(() => queryClient.invalidateQueries({ queryKey: ['me'] }))
    return () => {
      setUnauthorizedHandler(null)
      setAccessChangedHandler(null)
    }
  }, [navigate])
  return null
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <UnauthorizedRedirect />
          <ServerWakingBanner />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Navigate to="/resumes" replace />
                </ProtectedRoute>
              }
            />
            <Route
              path="/resumes"
              element={
                <ProtectedRoute>
                  <ResumesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/users/:userId"
              element={
                <ProtectedRoute requireAdmin>
                  <AdminViewPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
