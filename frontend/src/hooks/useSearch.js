import { useMutation } from '@tanstack/react-query'
import { useViewAs } from '../context/ViewAsContext.jsx'
import { api } from '../lib/api.js'

export function useSearch() {
  const { viewAsId } = useViewAs()
  return useMutation({
    /** @param {{query: string, topK?: number}} vars */
    mutationFn: ({ query, topK }) => api.search(query, topK, viewAsId),
  })
}
