const num = (value, fallback) => {
  const n = Number(value)
  return Number.isFinite(n) && n > 0 ? n : fallback
}

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')
export const MAX_FILE_MB = num(import.meta.env.VITE_MAX_FILE_MB, 1)
export const MAX_FILE_BYTES = Math.floor(MAX_FILE_MB * 1024 * 1024)
export const MAX_FILES_PER_UPLOAD = num(import.meta.env.VITE_MAX_FILES_PER_UPLOAD, 20)
export const MAX_PAGES = num(import.meta.env.VITE_MAX_PAGES, 2)
export const MAX_RESUMES_PER_USER = num(import.meta.env.VITE_MAX_RESUMES_PER_USER, 500)

/** @param {number} limit */
export const libraryFullMessage = (limit) =>
  `Library is full (${limit} resumes). Delete some resumes to add more.`

/** @param {number} limit */
export const reasonMessages = (limit) => ({
  not_a_pdf: 'Not a valid PDF.',
  file_too_large: `Larger than ${MAX_FILE_MB} MB.`,
  corrupted_pdf: 'File is corrupted.',
  password_protected: "Password-protected PDFs aren't supported.",
  too_many_pages: `More than ${MAX_PAGES} pages.`,
  duplicate: 'Already in your library.',
  too_many_files: `Too many files in one upload (max ${MAX_FILES_PER_UPLOAD}).`,
  library_full: libraryFullMessage(limit),
})
