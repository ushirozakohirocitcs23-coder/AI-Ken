import { useState } from 'react'
import { Search, ShieldPlus, Trash2 } from 'lucide-react'
import { api, qs } from '../../api'
import { useAuth } from '../../auth'
import { Alert, Badge, Button, ConfirmDialog, IconButton, Input, Modal, PageHeader, Select, fmtDate, useToast } from '../../components/ui'
import { Pager, Table, useApi } from './common'

const STATUS_TONE = { active: 'green', inactive: 'neutral', suspended: 'red' }

export default function Users() {
  const { user: me } = useAuth()
  const toast = useToast()
  const [f, setF] = useState({ q: '', role: '', status: '', page: 1 })
  const { data, error, reload } = useApi(`/admin/users${qs({ ...f, per_page: 15 })}`, [f])
  const [del, setDel] = useState(null)
  const [create, setCreate] = useState(null)
  const [cErr, setCErr] = useState('')

  const patch = async (u, body, msg) => {
    try { await api(`/admin/users/${u.id}`, { method: 'PATCH', body }); toast(msg); reload() }
    catch (e) { toast(e.message, 'error') }
  }
  const remove = async () => {
    try { await api(`/admin/users/${del.id}`, { method: 'DELETE' }); toast('Account deleted.'); setDel(null); reload() }
    catch (e) { toast(e.message, 'error') }
  }
  const createAdmin = async (e) => {
    e.preventDefault(); setCErr('')
    try { await api('/admin/users/admins', { method: 'POST', body: create }); toast('Administrator created.'); setCreate(null); reload() }
    catch (err) { setCErr(err.message) }
  }

  return (
    <>
      <PageHeader title="User Management" subtitle="Search accounts, change status or role. Users' stories and poems are never shown here."
        actions={<Button icon={ShieldPlus} onClick={() => setCreate({ full_name: '', email: '', password: '' })}>New administrator</Button>} />
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_160px_160px]">
        <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input value={f.q} onChange={e => setF({ ...f, q: e.target.value, page: 1 })} placeholder="Search name or email" aria-label="Search users"
            className="focus-ring w-full rounded-xl border border-ink-600 bg-ink-850 py-2.5 pl-9 pr-3 text-sm" /></div>
        <Select aria-label="Filter by role" value={f.role} onChange={e => setF({ ...f, role: e.target.value, page: 1 })}><option value="">All roles</option><option value="user">Users</option><option value="admin">Admins</option></Select>
        <Select aria-label="Filter by status" value={f.status} onChange={e => setF({ ...f, status: e.target.value, page: 1 })}><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option></Select>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <Table head={['Name', 'Role', 'Status', 'Poems', 'Registered', 'Last login', 'Actions']}
        empty={data?.users?.length === 0 && <p className="px-4 py-8 text-center text-sm text-ink-400">No users match these filters.</p>}>
        {data?.users?.map(u => (
          <tr key={u.id}>
            <td className="px-4 py-3"><p className="font-medium">{u.full_name}{u.id === me.id && <span className="ml-1 text-xs text-ink-400">(you)</span>}</p><p className="text-xs text-ink-400">{u.email}</p></td>
            <td className="px-4 py-3"><Badge tone={u.role === 'admin' ? 'iris' : 'neutral'}>{u.role}</Badge></td>
            <td className="px-4 py-3"><Badge tone={STATUS_TONE[u.status]}>{u.status}</Badge></td>
            <td className="px-4 py-3 tabular-nums">{u.poem_count}</td>
            <td className="px-4 py-3 text-xs text-ink-300">{fmtDate(u.created_at)}</td>
            <td className="px-4 py-3 text-xs text-ink-300">{fmtDate(u.last_login_at)}</td>
            <td className="px-4 py-3">
              {u.id !== me.id && (
                <div className="flex items-center gap-1">
                  <select aria-label={`Status for ${u.email}`} value={u.status} onChange={e => patch(u, { status: e.target.value }, `Account ${e.target.value}.`)}
                    className="focus-ring rounded-lg border border-ink-600 bg-ink-900 px-2 py-1 text-xs">
                    <option value="active">Active</option><option value="inactive">Inactive</option><option value="suspended">Suspended</option>
                  </select>
                  <Button size="sm" variant="ghost" onClick={() => patch(u, { role: u.role === 'admin' ? 'user' : 'admin' }, u.role === 'admin' ? 'Admin rights removed.' : 'Promoted to administrator.')}>
                    {u.role === 'admin' ? 'Make user' : 'Make admin'}</Button>
                  <IconButton label={`Delete ${u.email}`} icon={Trash2} className="hover:text-rose-300" onClick={() => setDel(u)} />
                </div>
              )}
            </td>
          </tr>
        ))}
      </Table>
      {data && <Pager page={data.page} total={data.total} perPage={data.per_page} onPage={p => setF({ ...f, page: p })} />}
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} onConfirm={remove} title="Delete account?"
        message={`${del?.email} and all of their conversations and poems will be permanently deleted.`} />
      <Modal open={!!create} onClose={() => setCreate(null)} title="Create administrator">
        {create && <form onSubmit={createAdmin} className="space-y-4">
          {cErr && <Alert tone="error">{cErr}</Alert>}
          <Input label="Full name" value={create.full_name} onChange={e => setCreate({ ...create, full_name: e.target.value })} />
          <Input label="Email" type="email" value={create.email} onChange={e => setCreate({ ...create, email: e.target.value })} />
          <Input label="Temporary password" type="password" hint="At least 8 characters with a letter and a number. Ask them to change it after first login." value={create.password} onChange={e => setCreate({ ...create, password: e.target.value })} />
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={() => setCreate(null)}>Cancel</Button><Button type="submit">Create admin</Button></div>
        </form>}
      </Modal>
    </>
  )
}
