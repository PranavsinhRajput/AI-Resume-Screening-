import { FileSearch } from 'lucide-react'
import ThemeToggle from '../components/layout/ThemeToggle.jsx'

export default function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="flex min-h-screen flex-col bg-app">
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>
      <main className="flex flex-1 items-start justify-center px-4 pb-12 sm:items-center">
        <div className="w-full max-w-md rounded-2xl border border-line bg-panel p-6 shadow-soft sm:p-8">
          <div className="mb-6 flex items-center gap-2">
            <FileSearch className="h-7 w-7 text-accent" aria-hidden="true" />
            <span className="text-lg font-semibold text-text">Resume Screening AI</span>
          </div>
          <h1 className="text-2xl font-bold text-text">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </div>
      </main>
    </div>
  )
}

export function Field({ id, label, ...inputProps }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-sm font-medium text-text">
        {label}
      </label>
      <input
        id={id}
        className="block min-h-11 w-full rounded-xl border border-line bg-panel px-3 text-text placeholder:text-muted"
        {...inputProps}
      />
    </div>
  )
}
