import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bookmark, Copy, ExternalLink, Pencil, Search, Trash2 } from 'lucide-react'
import { api, qs } from '../../api'
import { Badge, Button, ConfirmDialog, EmptyState, IconButton, Input, Modal, PageHeader, Spinner, fmtDate, useToast } from '../../components/ui'
import { ValidationReport } from './PoemCard'

const LANG = { fil: 'Filipino', en: 'English', taglish: 'Taglish' }

export default function SavedPoems() {
  const toast = useToast()
  const [poems, setPoems] = useState(null)
  const [q, setQ] = useState('')
  const [rename, setRename] = useState(null)
  const [del, setDel] = useState(null)
  const [report, setReport] = useState(null)

  const load = () => api(`/poems${qs({ saved: true, q })}`).then(r => setPoems(r.poems)).catch(e => toast(e.message, 'error'))
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t) }, [q]) // eslint-disable-line

  const doRename = async (e) => {
    e.preventDefault()
    await api(`/poems/${rename.id}`, { method: 'PATCH', body: { title: rename.title } })
    setRename(null); load(); toast('Poem renamed.')
  }
  const unsave = async (p) => { await api(`/poems/${p.id}`, { method: 'PATCH', body: { is_saved: false } }); load(); toast('Removed from saved poems.') }
  const doDelete = async () => { await api(`/poems/${del.id}`, { method: 'DELETE' }); setDel(null); load(); toast('Poem deleted.') }
  const copy = async (p) => { try { await navigator.clipboard.writeText(`${p.title}\n\n${p.content}`); toast('Copied.') } catch { toast('Copy failed.', 'error') } }

  return (
    <div className="scroll-thin flex-1 overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <PageHeader title="My Saved Poems" subtitle="Your collection — rename, revisit, copy or delete."
          actions={<div className="relative w-64"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
            <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search poems" aria-label="Search saved poems" className="focus-ring w-full rounded-xl border border-ink-600 bg-ink-850 py-2 pl-9 pr-3 text-sm" /></div>} />
        {poems === null ? <div className="flex justify-center py-16"><Spinner /></div> : poems.length === 0 ? (
          <EmptyState icon={Bookmark} title={q ? 'No saved poems match your search' : 'No saved poems yet'} action={<Link to="/app"><Button>Write a poem</Button></Link>}>
            Tap the bookmark on any poem to keep it here.
          </EmptyState>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {poems.map(p => (
              <article key={p.id} className="flex flex-col rounded-2xl border border-ink-700 bg-ink-850 p-5">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="font-serif text-lg font-semibold leading-tight">{p.title}</h2>
                  <div className="flex shrink-0">
                    <IconButton label="Copy" icon={Copy} onClick={() => copy(p)} />
                    <IconButton label="Rename" icon={Pencil} onClick={() => setRename({ id: p.id, title: p.title })} />
                    <IconButton label="Delete" icon={Trash2} className="hover:text-rose-300" onClick={() => setDel(p)} />
                  </div>
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1.5"><Badge tone="iris">{p.validation?.form_name || p.poem_type}</Badge><Badge>{LANG[p.language]}</Badge>
                  <button onClick={() => setReport(p)} className="focus-ring rounded-full"><Badge tone={p.validation?.overall === 'pass' ? 'green' : p.validation?.overall === 'fail' ? 'amber' : 'blue'}>Report</Badge></button></div>
                <p className="poem-text mt-3 flex-1 text-[15px] text-ink-100">{p.content}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-ink-400">
                  <span>{fmtDate(p.created_at)}</span>
                  <div className="flex gap-1">
                    <Button size="sm" variant="ghost" onClick={() => unsave(p)}>Unsave</Button>
                    {p.conversation_id && <Link to={`/app/c/${p.conversation_id}`}><Button size="sm" variant="ghost" icon={ExternalLink}>Open chat</Button></Link>}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
      <Modal open={!!rename} onClose={() => setRename(null)} title="Rename poem">
        {rename && <form onSubmit={doRename} className="space-y-4">
          <Input label="Title" value={rename.title} maxLength={200} onChange={e => setRename({ ...rename, title: e.target.value })} />
          <div className="flex justify-end gap-2"><Button variant="secondary" type="button" onClick={() => setRename(null)}>Cancel</Button><Button type="submit" disabled={!rename.title.trim()}>Save</Button></div>
        </form>}
      </Modal>
      <Modal open={!!report} onClose={() => setReport(null)} title="Validation report" wide>{report && <ValidationReport v={report.validation} />}</Modal>
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} onConfirm={doDelete} title="Delete poem?" message={`“${del?.title}” will be permanently deleted.`} />
    </div>
  )
}
