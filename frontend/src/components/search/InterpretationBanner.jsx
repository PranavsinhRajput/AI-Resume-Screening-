import { AlertTriangle, Info, Sparkles } from 'lucide-react'
import { describeFilters, filterLabel } from '../../lib/format.js'
import Chip from '../ui/Chip.jsx'

const WARN =
  'flex items-start gap-2 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100'

/** @param {{response: import('../../lib/types').SearchResponse}} props */
export default function InterpretationBanner({ response }) {
  const it = response.interpretation
  const filters = describeFilters(it.filters)
  const searchingFor = [...filters, it.used_raw_query ? null : it.summary].filter(Boolean)

  return (
    <div className="space-y-2" aria-live="polite">
      <div className="rounded-xl border border-line bg-panel p-3 shadow-soft">
        <div className="flex items-start gap-2 text-sm text-text">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
          <p className="min-w-0 break-words">
            <span className="font-semibold">Searching for: </span>
            {searchingFor.length ? searchingFor.join(' · ') : it.semantic_query}
          </p>
        </div>
        {(it.filters.required_skills.length > 0 || it.preferred_skills.length > 0 || it.verify_criteria.length > 0) && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {it.preferred_skills.map((s) => (
              <Chip key={`p-${s}`}>preferred: {s}</Chip>
            ))}
            {it.verify_criteria.map((c) => (
              <Chip key={`c-${c.text}`}>
                {c.required ? 'check' : 'nice to have'}: {c.text}
              </Chip>
            ))}
          </div>
        )}
      </div>

      {it.unsupported.map((u) => (
        <div key={u.text} className={WARN}>
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            Ignored: “{u.text}” — {u.reason || "the system doesn't filter on personal attributes."}
          </p>
        </div>
      ))}

      {it.relaxed_filters.length > 0 && (
        <div className={WARN}>
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>No exact matches. Relaxed: {it.relaxed_filters.map(filterLabel).join(', ')}.</p>
        </div>
      )}

      {it.used_raw_query && (
        <div className={WARN}>
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            Your request didn't name a role or skills, so these are the closest matches to your wording. Try naming a
            role or skills for better results.
          </p>
        </div>
      )}

      {response.parse_degraded && (
        <div className={WARN}>
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>
            The AI couldn't interpret your request right now, so no filters were applied — results match your wording
            directly.
          </p>
        </div>
      )}

      {response.llm_degraded && (
        <div className={WARN}>
          <Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <p>AI explanations are temporarily unavailable; results are ranked by similarity.</p>
        </div>
      )}
    </div>
  )
}
