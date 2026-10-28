import { useState } from 'react'
import { Search } from 'lucide-react'
import { qs } from '../../api'
import { Alert, Badge, PageHeader, fmtDate } from '../../components/ui'
import { Pager, Table, useApi } from './common'

const tone = (a) => a.includes('failed') || a.includes('blocked') || a.includes('deleted') ? 'red' : a.startsWith('admin.') ? 'iris' : a.startsWith('system.') ? 'amber' : 'neutral'

export default function AuditLogs() {
  const [f, setF] = useState({ action: '', page: 1 })
  const { data, error } = useApi(`/admin/audit-logs${qs({ ...f, per_page: 30 })}`, [f])
  return (
    <>
      <PageHeader title="Security & Audit Logs" subtitle="Authentication, security and administrative events. Passwords and personal stories are never logged." />
      <div className="relative mb-4 max-w-md"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
        <input value={f.action} onChange={e => setF({ action: e.target.value, page: 1 })} placeholder="Filter by action (e.g. login, admin.)" aria-label="Filter actions"
          className="focus-ring w-full rounded-xl border border-ink-600 bg-ink-850 py-2.5 pl-9 pr-3 text-sm" /></div>
      {error && <Alert tone="error">{error}</Alert>}
      <Table head={['Time', 'Action', 'Actor', 'Target', 'Details', 'IP']}>
        {data?.logs?.map(l => (
          <tr key={l.id} className="align-top">
            <td className="whitespace-nowrap px-4 py-2.5 text-xs text-ink-400">{fmtDate(l.at)}</td>
            <td className="px-4 py-2.5"><Badge tone={tone(l.action)}>{l.action}</Badge></td>
            <td className="px-4 py-2.5 text-xs">{l.actor || (l.actor_id ? `#${l.actor_id}` : 'system')}</td>
            <td className="px-4 py-2.5 text-xs text-ink-300">{l.target || '—'}</td>
            <td className="max-w-xs px-4 py-2.5 font-mono text-[11px] text-ink-400">{l.meta ? JSON.stringify(l.meta) : ''}</td>
            <td className="px-4 py-2.5 text-xs text-ink-400">{l.ip || ''}</td>
          </tr>
        ))}
      </Table>
      {data && <Pager page={data.page} total={data.total} perPage={30} onPage={p => setF({ ...f, page: p })} />}
    </>
  )
}
