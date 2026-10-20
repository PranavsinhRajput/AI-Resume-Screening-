import { supabase } from './supabase.js'
import { API_BASE_URL } from './config.js'

export const SESSION_EXPIRED_MESSAGE = 'Your session expired. Please log in again.'
const SLOW_REQUEST_MS = 5000

export class ApiError extends Error {
  /**
   * @param {number} status
   * @param {string} code
   * @param {string} message
   */
  constructor(status, code, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

// ---------- slow-request tracking (feeds the "server waking up" banner) ----------
let slowCount = 0
const slowListeners = new Set()

/** @param {(slow: boolean) => void} fn */
export function subscribeSlowRequests(fn) {
  slowListeners.add(fn)
  return () => slowListeners.delete(fn)
}

function setSlow(delta) {
  slowCount = Math.max(0, slowCount + delta)
  for (const fn of slowListeners) fn(slowCount > 0)
}

/** Wraps a promise so that if it takes > 5 s the global slow flag is on until it settles. */
function trackSlow(promise) {
  let flagged = false
  const timer = setTimeout(() => {
    flagged = true
    setSlow(1)
  }, SLOW_REQUEST_MS)
  return promise.finally(() => {
    clearTimeout(timer)
    if (flagged) setSlow(-1)
  })
}

// ---------- 401 handling ----------
let unauthorizedHandler = null

/** @param {() => void} fn called after sign-out on any 401 */
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

async function handleUnauthorized() {
  try {
    await supabase.auth.signOut()
  } catch {
    // ignore: the session is already invalid
  }
  if (unauthorizedHandler) unauthorizedHandler()
}

async function authHeader() {
  const { data } = await supabase.auth.getSession()
  const token = data?.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function parseError(response) {
  let code = 'internal_error'
  let message = 'Something went wrong. Please try again.'
  try {
    const body = await response.json()
    if (body?.error) {
      code = body.error.code || code
      message = body.error.message || message
    }
  } catch {
    // non-JSON error body
  }
  return new ApiError(response.status, code, message)
}

// ---------- 403 access changes (account pending/rejected while signed in) ----------
const ACCESS_CODES = new Set(['pending_approval', 'account_rejected'])
let accessChangedHandler = null

/** @param {() => void} fn called when the API says the account is no longer approved */
export function setAccessChangedHandler(fn) {
  accessChangedHandler = fn
}

/**
 * @param {string} path
 * @param {{method?: string, body?: any, headers?: Record<string,string>, signal?: AbortSignal, viewAs?: string|null}} [options]
 *   viewAs: an admin reading another user's library (sent as X-View-As; the backend checks the role).
 */
export async function request(path, options = {}) {
  const { method = 'GET', body, headers = {}, signal, viewAs } = options
  const isForm = typeof FormData !== 'undefined' && body instanceof FormData
  const finalHeaders = { ...(await authHeader()), ...headers }
  if (viewAs) finalHeaders['X-View-As'] = viewAs
  if (body !== undefined && !isForm) finalHeaders['Content-Type'] = 'application/json'

  let response
  try {
    response = await trackSlow(
      fetch(`${API_BASE_URL}${path}`, {
        method,
        headers: finalHeaders,
        body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
        signal,
      }),
    )
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError(0, 'network_error', "Can't reach the server. Check your connection and try again.")
  }

  if (response.status === 401) {
    await handleUnauthorized()
    throw new ApiError(401, 'unauthorized', SESSION_EXPIRED_MESSAGE)
  }
  if (!response.ok) {
    const error = await parseError(response)
    if (response.status === 403 && ACCESS_CODES.has(error.code) && accessChangedHandler) accessChangedHandler()
    throw error
  }
  if (response.status === 204) return null
  const text = await response.text()
  return text ? JSON.parse(text) : null
}

/**
 * Multipart upload with progress via XHR.
 * @param {File[]} files
 * @param {(fraction: number) => void} [onProgress]
 * @returns {Promise<import('./types').UploadResult>}
 */
export async function uploadFiles(files, onProgress) {
  const headers = await authHeader()
  const form = new FormData()
  for (const f of files) form.append('files', f, f.name)

  const promise = new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE_URL}/resumes`)
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total)
    }
    xhr.onerror = () =>
      reject(new ApiError(0, 'network_error', "Can't reach the server. Check your connection and try again."))
    xhr.onload = async () => {
      let body = null
      try {
        body = xhr.responseText ? JSON.parse(xhr.responseText) : null
      } catch {
        body = null
      }
      if (xhr.status === 401) {
        await handleUnauthorized()
        reject(new ApiError(401, 'unauthorized', SESSION_EXPIRED_MESSAGE))
        return
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(
          new ApiError(
            xhr.status,
            body?.error?.code || 'internal_error',
            body?.error?.message || 'Something went wrong. Please try again.',
          ),
        )
        return
      }
      resolve(body)
    }
    xhr.send(form)
  })
  return trackSlow(promise)
}

export const api = {
  health: (signal) =>
    fetch(`${API_BASE_URL}/health`, { signal }).then((r) => {
      if (!r.ok) throw new Error('unhealthy')
      return r.json()
    }),
  /** @returns {Promise<import('./types').Me>} */
  me: () => request('/me'),
  /** @returns {Promise<import('./types').ResumeStats>} */
  stats: (viewAs) => request('/resumes/stats', { viewAs }),
  /** @returns {Promise<import('./types').Page<import('./types').ResumeSummary>>} */
  listResumes: ({ status, page = 1, pageSize = 20 }, viewAs) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (status) params.set('status', status)
    return request(`/resumes?${params}`, { viewAs })
  },
  /** @returns {Promise<import('./types').ResumeDetail>} */
  getResume: (id, viewAs) => request(`/resumes/${encodeURIComponent(id)}`, { viewAs }),
  downloadUrl: (id, viewAs) => request(`/resumes/${encodeURIComponent(id)}/download-url`, { viewAs }),
  retry: (id) => request(`/resumes/${encodeURIComponent(id)}/retry`, { method: 'POST' }),
  remove: (id) => request(`/resumes/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  /** @returns {Promise<import('./types').SearchResponse>} */
  search: (query, topK, viewAs) =>
    request('/search', { method: 'POST', body: topK ? { query, top_k: topK } : { query }, viewAs }),

  admin: {
    /** @returns {Promise<{pending: number, approved: number, rejected: number}>} */
    stats: () => request('/admin/stats'),
    /** @returns {Promise<import('./types').AdminUser[]>} */
    users: (status) => request(`/admin/users${status ? `?status=${encodeURIComponent(status)}` : ''}`),
    approve: (id) => request(`/admin/users/${encodeURIComponent(id)}/approve`, { method: 'POST' }),
    reject: (id) => request(`/admin/users/${encodeURIComponent(id)}/reject`, { method: 'POST' }),
  },
}

/**
 * Open a resume PDF in a new tab. The tab is opened synchronously on click (avoids mobile popup
 * blockers) and navigated once the signed URL arrives.
 * @param {string} resumeId
 * @param {string|null} [viewAs]
 */
export async function openResumePdf(resumeId, viewAs) {
  const win = window.open('', '_blank')
  try {
    const { url } = await api.downloadUrl(resumeId, viewAs)
    if (win) {
      win.opener = null
      win.location.href = url
    } else {
      window.open(url, '_blank', 'noopener')
    }
  } catch (err) {
    if (win) win.close()
    throw err
  }
}
