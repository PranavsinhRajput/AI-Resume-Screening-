import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api.js'

export function useAdminStats() {
  return useQuery({ queryKey: ['admin', 'stats'], queryFn: api.admin.stats, refetchInterval: 30000 })
}

/** @param {'pending'|'approved'|'rejected'} status */
export function useAdminUsers(status) {
  return useQuery({
    queryKey: ['admin', 'users', status],
    queryFn: () => api.admin.users(status),
    // New sign-ups show up without a reload.
    refetchInterval: status === 'pending' ? 15000 : false,
  })
}

function useAdminMutation(fn) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSettled: () => qc.invalidateQueries({ queryKey: ['admin'] }),
  })
}

export const useApproveUser = () => useAdminMutation((id) => api.admin.approve(id))
export const useRejectUser = () => useAdminMutation((id) => api.admin.reject(id))
