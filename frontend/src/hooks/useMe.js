import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext.jsx'
import { api } from '../lib/api.js'

/** Current user's role and approval status. Pending users re-check every 15 s until approved. */
export function useMe() {
  const { user } = useAuth()
  return useQuery({
    queryKey: ['me', user?.id ?? null],
    queryFn: api.me,
    enabled: !!user,
    staleTime: 30000,
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 15000 : false),
  })
}
