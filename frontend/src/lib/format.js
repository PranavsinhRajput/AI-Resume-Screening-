/**
 * Format total experience months: 0 → "Fresher (0 yrs)", 28 → "2 yrs 4 mos", 12 → "1 yr", 5 → "5 mos".
 * @param {number|null|undefined} months
 * @returns {string}
 */
export function formatExperience(months) {
  if (months === null || months === undefined || Number.isNaN(months)) return '—'
  if (months <= 0) return 'Fresher (0 yrs)'
  const years = Math.floor(months / 12)
  const rem = months % 12
  const parts = []
  if (years) parts.push(`${years} ${years === 1 ? 'yr' : 'yrs'}`)
  if (rem) parts.push(`${rem} ${rem === 1 ? 'mo' : 'mos'}`)
  return parts.join(' ')
}

/**
 * @param {string|null|undefined} iso
 * @returns {string}
 */
export function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * @param {string|null|undefined} text
 * @param {number} max
 * @returns {string}
 */
export function truncate(text, max) {
  if (!text) return ''
  if (text.length <= max) return text
  return text.slice(0, Math.max(0, max - 1)).trimEnd() + '…'
}

/**
 * "2021-03" → "Mar 2021", "2021" → "2021".
 * @param {string|null|undefined} value
 * @returns {string}
 */
export function formatYearMonth(value) {
  if (!value) return ''
  const m = /^(\d{4})-(\d{1,2})$/.exec(value)
  if (!m) return value
  const date = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, 1))
  return date.toLocaleString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' })
}

/**
 * Human-readable filter labels for the interpretation banner.
 * @param {{min_experience_months: number|null, max_experience_months: number|null, required_skills: string[], location: string|null}} filters
 * @returns {string[]}
 */
export function describeFilters(filters) {
  if (!filters) return []
  const out = []
  if (filters.min_experience_months != null) out.push(`experience ≥ ${filters.min_experience_months} months`)
  if (filters.max_experience_months != null) out.push(`experience ≤ ${filters.max_experience_months} months`)
  for (const s of filters.required_skills || []) out.push(`must know ${s}`)
  if (filters.location) out.push(`location: ${filters.location}`)
  return out
}

const FILTER_LABELS = {
  location: 'location',
  required_skills: 'required skills',
  max_experience_months: 'maximum experience',
  min_experience_months: 'minimum experience',
}

/**
 * @param {string} name
 * @returns {string}
 */
export function filterLabel(name) {
  return FILTER_LABELS[name] || name
}
