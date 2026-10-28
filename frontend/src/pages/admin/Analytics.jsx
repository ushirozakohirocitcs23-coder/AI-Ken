import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Alert, Card, PageHeader, Spinner, cx } from '../../components/ui'
import { CHART, Stat, tooltipStyle, useApi } from './common'

const LANG = { fil: 'Filipino', en: 'English', taglish: 'Taglish' }
const VAL = { pass: 'Verified', pass_estimate: 'Passed (estimates)', fail: 'Adaptation', unknown: 'Unknown' }

function HBar({ data, dataKey = 'count', nameKey, color = CHART.iris, height }) {
  return (
    <div style={{ height: height || Math.max(140, data.length * 30 + 20) }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 16 }}>
          <CartesianGrid stroke={CHART.grid} horizontal={false} />
          <XAxis type="number" allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey={nameKey} width={110} tick={{ fill: '#a3adc6', fontSize: 12 }} axisLine={false} tickLine={false} />
          <Tooltip {...tooltipStyle} />
          <Bar dataKey={dataKey} name="Count" fill={color} radius={[0, 6, 6, 0]} barSize={16} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Analytics() {
  const [days, setDays] = useState(30)
  const { data: a, error } = useApi(`/admin/analytics?days=${days}`, [days])
  if (error) return <Alert tone="error">{error}</Alert>
  const total = a?.poems_by_date?.reduce((s, d) => s + d.poems, 0)
  return (
    <>
      <PageHeader title="Poetry Analytics" subtitle="Aggregate counts only — no story or poem text is used."
        actions={<div className="flex rounded-xl border border-ink-600 p-0.5">{[7, 30, 90].map(d => (
          <button key={d} onClick={() => setDays(d)} className={cx('focus-ring rounded-lg px-3 py-1.5 text-xs', days === d ? 'bg-ink-700 text-ink-100' : 'text-ink-400')}>{d} days</button>))}</div>} />
      {!a ? <Spinner /> : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat label="Poems" value={total} sub={`last ${days} days`} />
            <Stat label="Translations" value={a.kinds.translation || 0} sub={`${a.kinds.regeneration || 0} regenerations`} tone="sky" />
            <Stat label="Average rating" value={a.ratings.average ?? '—'} sub={`${a.ratings.count} ratings`} tone="amber" />
            <Stat label="Verified structure" value={total ? `${Math.round(((a.validation.pass || 0) + (a.validation.pass_estimate || 0)) / total * 100)}%` : '—'} sub="passed validation" tone="green" />
          </div>
          <Card className="p-5">
            <h2 className="mb-4 text-sm font-semibold">Poems generated and new sign-ups by date</h2>
            <div className="h-64"><ResponsiveContainer width="100%" height="100%">
              <LineChart data={a.poems_by_date} margin={{ left: -20, right: 8 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} />
                <XAxis dataKey="date" tick={{ fill: CHART.axis, fontSize: 11 }} tickFormatter={d => d.slice(5)} minTickGap={24} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: CHART.axis, fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...tooltipStyle} />
                <Line type="monotone" dataKey="poems" name="Poems" stroke={CHART.iris} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="signups" name="Sign-ups" stroke={CHART.sky} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer></div>
          </Card>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card className="p-5"><h2 className="mb-3 text-sm font-semibold">Most selected poem forms</h2>{a.forms.length ? <HBar data={a.forms} nameKey="name" /> : <p className="text-sm text-ink-400">No data yet.</p>}</Card>
            <Card className="p-5"><h2 className="mb-3 text-sm font-semibold">Emotion categories (aggregate)</h2>{a.emotions.length ? <HBar data={a.emotions} nameKey="label" color={CHART.sky} /> : <p className="text-sm text-ink-400">No data yet.</p>}</Card>
            <Card className="p-5"><h2 className="mb-3 text-sm font-semibold">Output languages</h2>{a.languages.length ? <HBar data={a.languages.map(l => ({ ...l, name: LANG[l.language] || l.language }))} nameKey="name" color={CHART.green} /> : <p className="text-sm text-ink-400">No data yet.</p>}</Card>
            <Card className="p-5">
              <h2 className="mb-3 text-sm font-semibold">Feedback ratings</h2>
              <HBar data={[5, 4, 3, 2, 1].map(n => ({ name: `${n} ★`, count: a.ratings.distribution[n] }))} nameKey="name" color={CHART.amber} height={180} />
              <h2 className="mb-2 mt-4 text-sm font-semibold">Validation outcomes</h2>
              <div className="flex flex-wrap gap-2 text-xs">{Object.entries(a.validation).map(([k, v]) => <span key={k} className="rounded-lg bg-ink-800 px-2.5 py-1.5">{VAL[k] || k}: <b className="tabular-nums">{v}</b></span>)}</div>
            </Card>
          </div>
        </div>
      )}
    </>
  )
}
