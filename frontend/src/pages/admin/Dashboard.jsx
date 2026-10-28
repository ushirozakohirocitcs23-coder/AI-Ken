import { Activity, BookHeart, MessagesSquare, Star, Users } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Alert, Badge, Card, PageHeader, Spinner, fmtDate } from '../../components/ui'
import { CHART, Stat, tooltipStyle, useApi } from './common'

function ServiceRow({ name, ok, detail, warn }) {
  return (
    <div className="flex items-center justify-between gap-3 py-2.5 text-sm">
      <span>{name}</span>
      <span className="flex items-center gap-2 text-right text-xs text-ink-400"><span className="hidden sm:inline">{detail}</span>
        <Badge tone={ok ? (warn ? 'amber' : 'green') : 'red'}>{ok ? (warn ? 'Limited' : 'Operational') : 'Not configured'}</Badge></span>
    </div>
  )
}

export default function Dashboard() {
  const { data: o, error } = useApi('/admin/overview')
  const { data: an } = useApi('/admin/analytics?days=30')
  if (error) return <Alert tone="error">{error}</Alert>
  if (!o) return <div className="flex justify-center py-20"><Spinner /></div>
  const s = o.services
  return (
    <>
      <PageHeader title="Dashboard" subtitle="System overview from live database records." />
      {!s.ai.configured && <Alert tone="warn" title="AI service not configured" className="mb-5">{s.ai.setup_hint}</Alert>}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Registered users" value={o.users.total} sub={`${o.users.active} active · ${o.users.inactive} inactive · ${o.users.suspended} suspended`} icon={Users} />
        <Stat label="Poems generated" value={o.poems.total} sub={`${o.poems.last_7d} in the last 7 days · ${o.poems.saved} saved`} icon={BookHeart} tone="sky" />
        <Stat label="Conversations" value={o.conversations} sub={`${o.users.logged_in_last_7d} user${o.users.logged_in_last_7d === 1 ? '' : 's'} active this week`} icon={MessagesSquare} tone="green" />
        <Stat label="Avg. rating" value={o.feedback.average ? `${o.feedback.average} / 5` : '—'} sub={`${o.feedback.count} ratings`} icon={Star} tone="amber" />
      </div>
      <div className="mt-5 grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold">Poems generated — last 30 days</h2>
          <div className="h-64">
            {an ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={an.poems_by_date} margin={{ left: -20, right: 8 }}>
                  <defs><linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={CHART.iris} stopOpacity={0.4} /><stop offset="1" stopColor={CHART.iris} stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid stroke={CHART.grid} vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: CHART.axis, fontSize: 11 }} tickFormatter={d => d.slice(5)} minTickGap={24} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip {...tooltipStyle} />
                  <Area type="monotone" dataKey="poems" name="Poems" stroke={CHART.iris} strokeWidth={2} fill="url(#ar)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : <Spinner />}
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Activity className="h-4 w-4 text-iris-400" /> AI & RAG services</h2>
          <div className="divide-y divide-ink-700">
            <ServiceRow name="Language model" ok={s.ai.configured} detail={`${s.ai.provider} · ${s.ai.model}`} />
            <ServiceRow name="Embeddings" ok={s.embeddings.configured} warn={s.embeddings.provider === 'local'} detail={s.embeddings.model} />
            <ServiceRow name="Vector store" ok={s.vector_store.ok} detail={`${s.vector_store.chunks_current_model} chunks · ${s.vector_store.probe_ms} ms`} />
            <ServiceRow name="Database" ok={s.database.ok} detail="connected" />
          </div>
          {s.embeddings.provider === 'local' && <p className="mt-2 text-xs text-ink-400">{s.embeddings.note}</p>}
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
            {Object.entries(s.pipeline_24h).map(([k, v]) => (
              <div key={k} className="rounded-lg bg-ink-800 px-2.5 py-1.5"><span className="capitalize text-ink-400">{k}</span> <span className="float-right tabular-nums">{v.last_24h}{v.failed ? <span className="text-rose-300"> · {v.failed}✕</span> : ''}</span></div>
            ))}
          </div>
        </Card>
      </div>
      <Card className="mt-5 p-5">
        <h2 className="mb-3 text-sm font-semibold">Recent system activity</h2>
        {o.recent_activity.length === 0 ? <p className="text-sm text-ink-400">No activity yet.</p> : (
          <ul className="divide-y divide-ink-700 text-sm">
            {o.recent_activity.map((a, i) => (
              <li key={i} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span><code className="rounded bg-ink-800 px-1.5 py-0.5 text-xs text-iris-300">{a.action}</code> <span className="text-ink-300">{a.actor || 'system'}</span> {a.target && <span className="text-ink-400">→ {a.target}</span>}</span>
                <span className="text-xs text-ink-400">{fmtDate(a.at)}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  )
}
