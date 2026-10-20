import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { MailCheck } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import Button from '../components/ui/Button.jsx'
import AuthLayout, { Field } from './AuthLayout.jsx'

const MIN_PASSWORD = 8

export default function SignupPage() {
  const { session, signUp } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmSent, setConfirmSent] = useState(false)

  if (session && !confirmSent) return <Navigate to="/resumes" replace />

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (password.length < MIN_PASSWORD) {
      setError(`Password must be at least ${MIN_PASSWORD} characters.`)
      return
    }
    setBusy(true)
    try {
      const { needsConfirmation } = await signUp(email.trim(), password)
      if (needsConfirmation) setConfirmSent(true)
      else navigate('/resumes', { replace: true })
    } catch (err) {
      setError(err?.message || 'Could not sign up.')
    } finally {
      setBusy(false)
    }
  }

  if (confirmSent) {
    return (
      <AuthLayout title="Check your email">
        <div role="status" className="flex items-start gap-3 text-sm text-text">
          <MailCheck className="h-6 w-6 shrink-0 text-accent" aria-hidden="true" />
          <p>Check your email to confirm your account. Then come back and log in.</p>
        </div>
        <Link
          to="/login"
          className="mt-6 inline-block font-medium text-accent-strong underline-offset-2 hover:underline"
        >
          Go to login
        </Link>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Create your account" subtitle="One private resume library per account.">
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
          label={`Password (min ${MIN_PASSWORD} characters)`}
          type="password"
          autoComplete="new-password"
          minLength={MIN_PASSWORD}
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
          Sign up
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent-strong underline-offset-2 hover:underline">
          Log in
        </Link>
      </p>
    </AuthLayout>
  )
}
