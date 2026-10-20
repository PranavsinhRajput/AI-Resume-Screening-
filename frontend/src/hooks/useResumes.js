import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useViewAs } from '../context/ViewAsContext.jsx'
import { api, uploadFiles } from '../lib/api.js'

const POLL_MS = 3000
export const PAGE_SIZE = 20

/** @param {import('../lib/types').ResumeStats|undefined} stats */
export function isProcessing(stats) {
  return !!stats && stats.pending + stats.processing > 0
}

// Query keys always carry the library being viewed (own = null) so caches never mix (DI-7).
export function useResumeStats() {
  const { viewAsId } = useViewAs()
  return useQuery({
    queryKey: ['resumes', viewAsId, 'stats'],
    queryFn: () => api.stats(viewAsId),
    refetchInterval: (query) => (isProcessing(query.state.data) ? POLL_MS : false),
  })
}

/**
 * @param {{status?: string, page: number}} params
 * @param {import('../lib/types').ResumeStats|undefined} stats
 */
export function useResumeList({ status, page }, stats) {
  const { viewAsId } = useViewAs()
  return useQuery({
    queryKey: ['resumes', viewAsId, { status: status || null, page }],
    queryFn: () => api.listResumes({ status, page, pageSize: PAGE_SIZE }, viewAsId),
    refetchInterval: isProcessing(stats) ? POLL_MS : false,
    placeholderData: (prev) => prev,
  })
}

/** @param {string|null} id */
export function useResumeDetail(id) {
  const { viewAsId } = useViewAs()
  return useQuery({
    queryKey: ['resume', viewAsId, id],
    queryFn: () => api.getResume(id, viewAsId),
    enabled: !!id,
  })
}

function useInvalidate() {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: ['resumes'] })
    qc.invalidateQueries({ queryKey: ['resume'] })
  }
}

export function useUploadResumes() {
  const invalidate = useInvalidate()
  return useMutation({
    /** @param {{files: File[], onProgress?: (f: number) => void}} vars */
    mutationFn: ({ files, onProgress }) => uploadFiles(files, onProgress),
    onSettled: invalidate,
  })
}

export function useDeleteResume() {
  const invalidate = useInvalidate()
  return useMutation({ mutationFn: (id) => api.remove(id), onSettled: invalidate })
}

export function useRetryResume() {
  const invalidate = useInvalidate()
  return useMutation({ mutationFn: (id) => api.retry(id), onSettled: invalidate })
}
