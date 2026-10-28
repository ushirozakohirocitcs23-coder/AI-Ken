import { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../../api'
import { Card, IconButton, cx } from '../../components/ui'

export const CHART = { iris: '#a594f9', sky: '#6ea8fe', grid: '#1c2742', axis: '#7d89a8', green: '#34d399', amber: '#fbbf24', rose: '#fb7185' }
export const tooltipStyle = { contentStyle: { background: '#131b31', border: '1px solid #2a3656', borderRadius: 12, fontSize: 12, color: '#e6e9f2' }, labelStyle: { color: '#a3adc6' }, cursor: { fill: 'rgb(139 119 242 / 0.08)' } }

export function useApi(path, deps = []) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const reload = useCallback(() => {
    setLoading(true)
    return api(path).then(d => { setData(d); setError(null) }).catch(e => setError(e.message)).finally(() => setLoading(false))
  }, [path]) // eslint-disable-line
  useEffect(() => { reload() }, [reload, ...deps]) // eslint-disable-line
  return { data, error, loading, reload, setData }
}

export function Stat({ label, value, sub, icon: Icon, tone = 'iris' }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-wider text-ink-400">{label}</p>
        {Icon && <Icon className={cx('h-4 w-4', tone === 'iris' ? 'text-iris-400' : tone === 'green' ? 'text-emerald-400' : tone === 'amber' ? 'text-amber-400' : 'text-sky-400')} />}
      </div>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value ?? '—'}</p>
      {sub && <p className="mt-0.5 text-xs text-ink-400">{sub}</p>}
    </Card>
  )
}

export function Pager({ page, total, perPage, onPage }) {
  const pages = Math.max(1, Math.ceil(total / perPage))
  return (
    <div className="flex items-center justify-between px-1 pt-3 text-xs text-ink-400">
      <span>{total} total</span>
      <div className="flex items-center gap-1">
        <IconButton label="Previous page" icon={ChevronLeft} disabled={page <= 1} onClick={() => onPage(page - 1)} />
        <span>Page {page} of {pages}</span>
        <IconButton label="Next page" icon={ChevronRight} disabled={page >= pages} onClick={() => onPage(page + 1)} />
      </div>
    </div>
  )
}

export function Table({ head, children, empty }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-ink-700 bg-ink-850/80">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead className="border-b border-ink-700 text-xs uppercase tracking-wider text-ink-400"><tr>{head.map(h => <th key={h} className="px-4 py-3 font-medium">{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-ink-700/70">{children}</tbody>
      </table>
      {empty}
    </div>
  )
}
