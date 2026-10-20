import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-app px-4 text-center">
      <p className="text-5xl font-bold text-accent">404</p>
      <h1 className="text-xl font-semibold text-text">Page not found</h1>
      <Link
        to="/resumes"
        className="inline-flex min-h-11 items-center rounded-xl bg-accent px-4 font-semibold text-harvest-orange-950 shadow-button hover:bg-accent-strong"
      >
        Go to your resumes
      </Link>
    </main>
  )
}
