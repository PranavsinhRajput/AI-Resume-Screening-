import { describe, expect, it } from 'vitest'
import { describeFilters, formatExperience, formatYearMonth, truncate } from './format.js'

describe('formatExperience', () => {
  it('formats freshers', () => expect(formatExperience(0)).toBe('Fresher (0 yrs)'))
  it('formats years and months', () => expect(formatExperience(28)).toBe('2 yrs 4 mos'))
  it('formats a single year', () => expect(formatExperience(12)).toBe('1 yr'))
  it('formats months only', () => expect(formatExperience(5)).toBe('5 mos'))
  it('formats one month', () => expect(formatExperience(13)).toBe('1 yr 1 mo'))
  it('handles null', () => expect(formatExperience(null)).toBe('—'))
})

describe('truncate', () => {
  it('keeps short text', () => expect(truncate('abc', 5)).toBe('abc'))
  it('truncates long text', () => expect(truncate('abcdefgh', 5)).toBe('abcd…'))
  it('handles empty', () => expect(truncate(null, 5)).toBe(''))
})

describe('formatYearMonth', () => {
  it('passes through year only', () => expect(formatYearMonth('2021')).toBe('2021'))
  it('returns empty for null', () => expect(formatYearMonth(null)).toBe(''))
})

describe('describeFilters', () => {
  it('describes all filters', () => {
    expect(
      describeFilters({ min_experience_months: 24, max_experience_months: null, required_skills: ['python'], location: 'Pune' }),
    ).toEqual(['experience ≥ 24 months', 'must know python', 'location: Pune'])
  })
})
