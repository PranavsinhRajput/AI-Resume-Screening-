import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { Check, Eye, ShieldCheck, UserCheck, UserX, Users } from 'lucide-react'
import AppBar from '../components/layout/AppBar.jsx'
import Button from '../components/ui/Button.jsx'
import Chip from '../components/ui/Chip.jsx'
import Dialog from '../components/ui/Dialog.jsx'
import EmptyState from '../components/ui/EmptyState.jsx'
import ErrorState from '../components/ui/ErrorState.jsx'
import { SkeletonList } from '../components/ui/Skeleton.jsx'
import { useAdminStats, useAdminUsers, useApproveUser, useRejectUser } from '../hooks/useAdmin.js'
import { useMe } from '../hooks/useMe.js'
import { formatDate } from '../lib/format.js'

const TABS = [
  { id: 'pending', label: 'Pending requests', icon: UserCheck },
  { id: 'approved', label: 'Active users', icon: Users },
  { id: 'rejected', label: 'Rejected', icon: UserX },
]

const EMPTY = {
  pending: { title: 'No pending requests', text: 'New sign-ups will appear here for approval.' },
  approved: { title: 'No active users', text: 'Approved users will appear here.' },
  rejected: { title: 'No rejected users', text: 'Users you reject or revoke appear here.' },
}

function StatCard({ label, value, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={clsx(
        'min-h-11 rounded-2xl border bg-panel p-4 text-left shadow-soft transition-colors',
        active ? 'border-accent' : 'border-line hover:bg-elevated',
      )}
    >
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold text-text">{value ?? '—'}</p>
    </button>
  )
}

/**
 * Per-user actions depending on which list the user is in.
 * @param {{user: import('../lib/types').AdminUser, tab: string, isSelf: boolean}} props
 */
function UserActions({ user, tab, isSelf }) {
  const navigate = useNavigate()
  const approve = useApproveUser()
  const reject = useRejectUser()
  const [confirm, setConfirm] = useState(false)
  const [error, setError] = useState('')
  const onError = (err) => setError(err?.message || 'Something went wrong.')

  const viewAs = () => navigate(`/admin/users/${user.id}`, { state: { email: user.email } })

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap gap-2">
        {(tab === 'pending' || tab === 'rejected') && (
          <Button size="sm" loading={approve.isPending} onClick={() => approve.mutate(user.id, { onError })}>
            <Check className="h-4 w-4" aria-hidden="true" />
            Approve
          </Button>
        )}
        {tab === 'pending' && (
          <Button variant="secondary" size="sm" onClick={() => setConfirm(true)}>
            <UserX className="h-4 w-4" aria-hidden="true" />
            Reject
          </Button>
        )}
        {tab === 'approved' && !isSelf && (
          <Button variant="secondary" size="sm" onClick={viewAs} aria-label={`View ${user.email}'s library`}>
            <Eye className="h-4 w-4" aria-hidden="true" />
            View as user
          </Button>
        )}
        {tab === 'approved' && !isSelf && user.role !== 'admin' && (
          <Button variant="ghost" size="sm" onClick={() => setConfirm(true)}>
            <UserX className="h-4 w-4 text-red-600 dark:text-red-400" aria-hidden="true" />
            Revoke access
          </Button>
        )}
        {isSelf && <span className="text-xs text-muted">This is you</span>}
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
      <Dialog
        open={confirm}
        title={tab === 'pending' ? 'Reject this request?' : 'Revoke access?'}
        confirmLabel={tab === 'pending' ? 'Reject' : 'Revoke'}
        danger
        loading={reject.isPending}
        onCancel={() => setConfirm(false)}
        onConfirm={() =>
          reject.mutate(user.id, {
            onSuccess: () => setConfirm(false),
            onError: (err) => {
              setConfirm(false)
              onError(err)
            },
          })
        }
      >
        {tab === 'pending'
          ? `${user.email} won't be able to use the application. You can still approve them later from the Rejected list.`
          : `${user.email} will lose access immediately. Their resumes are kept, and you can approve them again later.`}
      </Dialog>
    </div>
  )
}

function RoleChip({ role }) {
  if (role !== 'admin') return null
  return (
    <Chip className="gap-1">
      <ShieldCheck className="h-3 w-3" aria-hidden="true" />
      admin
    </Chip>
  )
}

function UsersTable({ users, tab, meId }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-line bg-panel shadow-soft">
      <table className="w-full table-fixed text-left text-sm">
        <thead className="border-b border-line bg-elevated text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="w-[30%] px-4 py-3 font-medium">User</th>
            <th scope="col" className="px-4 py-3 font-medium">Signed up</th>
            {tab === 'approved' ? (
              <>
                <th scope="col" className="px-4 py-3 font-medium">Resumes</th>
                <th scope="col" className="hidden px-4 py-3 font-medium lg:table-cell">Last sign-in</th>
              </>
            ) : (
              <th scope="col" className="hidden px-4 py-3 font-medium lg:table-cell">
                {tab === 'rejected' ? 'Rejected' : 'Last sign-in'}
              </th>
            )}
            <th scope="col" className="w-[30%] px-4 py-3 font-medium">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-line last:border-b-0">
              <td className="px-4 py-3">
                <div className="flex min-w-0 items-center gap-2">
                  <span className="truncate font-medium text-text" title={u.email || ''}>
                    {u.email}
                  </span>
                  <RoleChip role={u.role} />
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-muted">{formatDate(u.created_at)}</td>
              {tab === 'approved' ? (
                <>
                  <td className="px-4 py-3 text-text">
                    {u.resume_count} <span className="text-xs text-muted">({u.done_count} ready)</span>
                  </td>
                  <td className="hidden px-4 py-3 text-xs text-muted lg:table-cell">
                    {formatDate(u.last_sign_in_at) || 'Never'}
                  </td>
                </>
              ) : (
                <td className="hidden px-4 py-3 text-xs text-muted lg:table-cell">
                  {tab === 'rejected' ? formatDate(u.reviewed_at) : formatDate(u.last_sign_in_at) || 'Never'}
                </td>
              )}
              <td className="px-4 py-3">
                <UserActions user={u} tab={tab} isSelf={u.id === meId} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function UserCards({ users, tab, meId }) {
  return (
    <ul className="space-y-3">
      {users.map((u) => (
        <li key={u.id} className="rounded-2xl border border-line bg-panel p-4 shadow-soft">
          <div className="flex min-w-0 items-center gap-2">
            <p className="truncate font-semibold text-text">{u.email}</p>
            <RoleChip role={u.role} />
          </div>
          <p className="mt-1 text-xs text-muted">Signed up {formatDate(u.created_at)}</p>
          {tab === 'approved' && (
            <p className="mt-1 text-sm text-text">
              {u.resume_count} resumes <span className="text-muted">({u.done_count} ready)</span>
            </p>
          )}
          <div className="mt-3">
            <UserActions user={u} tab={tab} isSelf={u.id === meId} />
          </div>
        </li>
      ))}
    </ul>
  )
}

export default function AdminPage() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab') : 'pending'
  const setTab = (t) => setParams({ tab: t }, { replace: true })
  const me = useMe()
  const stats = useAdminStats()
  const users = useAdminUsers(tab)

  return (
    <div className="min-h-screen bg-app">
      <AppBar />
      <main className="mx-auto max-w-7xl space-y-6 px-4 py-5 sm:px-6 sm:py-8">
        <div>
          <h1 className="text-2xl font-bold text-text">Admin panel</h1>
          <p className="mt-1 text-sm text-muted">
            Approve new sign-ups, manage access, and view any user's library (read-only).
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <StatCard label="Pending requests" value={stats.data?.pending} active={tab === 'pending'} onClick={() => setTab('pending')} />
          <StatCard label="Active users" value={stats.data?.approved} active={tab === 'approved'} onClick={() => setTab('approved')} />
          <StatCard label="Rejected" value={stats.data?.rejected} active={tab === 'rejected'} onClick={() => setTab('rejected')} />
        </div>

        <div role="tablist" aria-label="Users" className="flex gap-1 overflow-x-auto border-b border-line">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={tab === t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                '-mb-px inline-flex min-h-11 shrink-0 items-center gap-2 rounded-t-xl border-b-2 px-4 text-sm font-medium',
                tab === t.id ? 'border-accent bg-soft-accent text-text' : 'border-transparent text-muted hover:text-text',
              )}
            >
              <t.icon className="h-4 w-4" aria-hidden="true" />
              {t.label}
              {t.id === 'pending' && stats.data?.pending > 0 && (
                <span className="rounded-full bg-accent px-2 text-xs font-semibold text-harvest-orange-950">
                  {stats.data.pending}
                </span>
              )}
            </button>
          ))}
        </div>

        <div role="tabpanel" aria-live="polite">
          {users.isLoading && <SkeletonList rows={4} />}
          {users.error && <ErrorState error={users.error} onRetry={users.refetch} />}
          {users.data && users.data.length === 0 && (
            <EmptyState icon={Users} title={EMPTY[tab].title}>
              {EMPTY[tab].text}
            </EmptyState>
          )}
          {users.data && users.data.length > 0 && (
            <>
              <div className="hidden md:block">
                <UsersTable users={users.data} tab={tab} meId={me.data?.id} />
              </div>
              <div className="md:hidden">
                <UserCards users={users.data} tab={tab} meId={me.data?.id} />
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
