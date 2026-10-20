// JSDoc typedefs mirroring the backend API schemas (architecture.md §6.2). No runtime code.

/**
 * @typedef {'pending'|'processing'|'done'|'failed'} ResumeStatus
 */

/**
 * @typedef {Object} ResumeStats
 * @property {number} total
 * @property {number} done
 * @property {number} pending
 * @property {number} processing
 * @property {number} failed
 * @property {number} limit
 */

/**
 * @typedef {'not_a_pdf'|'file_too_large'|'corrupted_pdf'|'password_protected'|'too_many_pages'|'duplicate'|'too_many_files'|'library_full'} RejectReason
 */

/**
 * @typedef {Object} UploadResult
 * @property {{resume_id: string, filename: string}[]} accepted
 * @property {{filename: string, reason: RejectReason, message: string, existing_resume_id: string|null}[]} rejected
 */

/**
 * @typedef {Object} ResumeSummary
 * @property {string} id
 * @property {string} original_filename
 * @property {ResumeStatus} status
 * @property {string|null} error_message
 * @property {string|null} candidate_name
 * @property {number|null} total_experience_months
 * @property {string[]} skills
 * @property {string|null} location
 * @property {string} created_at
 */

/**
 * @typedef {Object} Experience
 * @property {string|null} company
 * @property {string|null} title
 * @property {string} employment_type
 * @property {string|null} start_date
 * @property {string|null} end_date
 * @property {boolean} is_current
 * @property {string|null} location
 * @property {string|null} description
 */

/**
 * @typedef {ResumeSummary & {
 *   email: string|null, phone: string|null,
 *   links: {linkedin?: string|null, github?: string|null, portfolio?: string|null},
 *   headline: string|null, summary: string|null,
 *   education: {institution: string|null, degree: string|null, field_of_study: string|null, start_year: number|null, end_year: number|null, grade: string|null}[],
 *   certifications: string[],
 *   projects: {name: string, description: string, technologies: string[]}[],
 *   experiences: Experience[],
 *   parse_warnings: string[]
 * }} ResumeDetail
 */

/**
 * @template T
 * @typedef {Object} Page
 * @property {T[]} items
 * @property {number} total
 * @property {number} page
 * @property {number} page_size
 */

/**
 * @typedef {Object} Interpretation
 * @property {string} summary
 * @property {{min_experience_months: number|null, max_experience_months: number|null, required_skills: string[], location: string|null}} filters
 * @property {string[]} preferred_skills
 * @property {string} semantic_query
 * @property {{text: string, required: boolean}[]} verify_criteria
 * @property {{text: string, reason: string}[]} unsupported
 * @property {string[]} relaxed_filters
 * @property {boolean} used_raw_query
 */

/**
 * @typedef {Object} SearchResult
 * @property {number} rank
 * @property {string} resume_id
 * @property {string|null} candidate_name
 * @property {string} original_filename
 * @property {number|null} total_experience_months
 * @property {string|null} location
 * @property {string[]} skills
 * @property {number} match_score
 * @property {number} vector_score
 * @property {string} reason
 * @property {boolean} meets_all_required
 * @property {{criterion: string, required: boolean, met: boolean|null, evidence: string|null}[]} criteria
 * @property {{section: string, text: string}[]} snippets
 */

/**
 * @typedef {Object} SearchResponse
 * @property {string} query
 * @property {Interpretation} interpretation
 * @property {boolean} llm_degraded
 * @property {boolean} parse_degraded
 * @property {number} candidates_considered
 * @property {SearchResult[]} results
 */

/**
 * @typedef {Object} Me
 * @property {string} id
 * @property {string|null} email
 * @property {'user'|'admin'} role
 * @property {'pending'|'approved'|'rejected'} status
 */

/**
 * @typedef {Object} AdminUser
 * @property {string} id
 * @property {string|null} email
 * @property {'user'|'admin'} role
 * @property {'pending'|'approved'|'rejected'} status
 * @property {string} created_at
 * @property {string|null} reviewed_at
 * @property {string|null} last_sign_in_at
 * @property {number} resume_count
 * @property {number} done_count
 */

export {}
