import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import Button from '../components/ui/Button.jsx'
import AuthLayout, { Field } from './AuthLayout.jsx'

export default function LoginPage() {
  const { session, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const notice = location.state?.message
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (session) return <Navigate to={location.state?.from || '/resumes'} replace />

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await signIn(email.trim(), password)
      navigate(location.state?.from || '/resumes', { replace: true })
    } catch (err) {
      setError(err?.message || 'Could not log in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout title="Log in" subtitle="Screen resumes with plain-language search.">
      {notice && (
        <p
          role="status"
          className="mb-4 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"
        >
          {notice}
        </p>
      )}
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Field
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Field
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && (
          <p role="alert" className="text-sm text-red-700 dark:text-red-300">
            {error}
          </p>
        )}
        <Button type="submit" loading={busy} className="w-full justify-center" disabled={!email || !password}>
          Log in
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        No account?{' '}
        <Link to="/signup" className="font-medium text-accent-strong underline-offset-2 hover:underline">
          Sign up
        </Link>
      </p>
    </AuthLayout>
  )
}
