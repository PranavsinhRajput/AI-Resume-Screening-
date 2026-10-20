import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import Button from '../ui/Button.jsx'

export const EXAMPLE_PROMPTS = [
  'Relevant resumes for the AI Engineer role',
  'Candidates with at least 2 years of experience who know Python',
  'Freshers with React projects',
]

const STAGES = ['Understanding your request…', 'Finding resumes…', 'Checking details…']

/**
 * @param {{onSearch: (q: string) => void, loading: boolean}} props
 */
export default function SearchBox({ onSearch, loading }) {
  const [query, setQuery] = useState('')
  const [stage, setStage] = useState(0)
  const trimmed = query.trim()
  const valid = trimmed.length >= 3 && trimmed.length <= 500

  useEffect(() => {
    if (!loading) {
      setStage(0)
      return
    }
    const timer = setInterval(() => setStage((s) => Math.min(s + 1, STAGES.length - 1)), 2500)
    return () => clearInterval(timer)
  }, [loading])

  const submit = (e) => {
    e?.preventDefault()
    if (valid && !loading) onSearch(trimmed)
  }

  return (
    <form onSubmit={submit} className="space-y-3" role="search">
      <label htmlFor="search-query" className="block text-sm font-medium text-text">
        Describe who you're looking for
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <textarea
          id="search-query"
          rows={2}
          maxLength={500}
          value={query}
          disabled={loading}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          placeholder="e.g. Python developers who have deployed ML models to production"
          className="min-h-11 w-full flex-1 resize-y rounded-xl border border-line bg-panel px-3 py-2.5 text-text placeholder:text-muted disabled:opacity-60"
        />
        <Button type="submit" disabled={!valid} loading={loading} className="justify-center sm:self-start">
          <Search className="h-4 w-4" aria-hidden="true" />
          Search
        </Button>
      </div>
      <div className="flex flex-wrap gap-2" aria-label="Example searches">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            disabled={loading}
            onClick={() => setQuery(p)}
            className="min-h-11 rounded-full border border-line bg-soft-accent px-3 py-1 text-left text-xs text-text hover:border-accent md:min-h-8"
          >
            {p}
          </button>
        ))}
      </div>
      <p aria-live="polite" className="min-h-5 text-sm text-muted">
        {loading ? STAGES[stage] : ''}
      </p>
    </form>
  )
}
