import { useState } from 'react'
import { Eye, FlaskConical, RefreshCw, Trash2, Upload } from 'lucide-react'
import { api, qs } from '../../api'
import { Alert, Badge, Button, Card, ConfirmDialog, IconButton, Input, Modal, PageHeader, Select, Spinner, Textarea, cx, fmtDate, useToast } from '../../components/ui'
import { Stat, Table, useApi } from './common'

const STATUS = { ready: 'green', processing: 'blue', pending: 'neutral', error: 'red' }
const TYPES = { poetry_rules: 'Poetry rules', technique: 'Literary technique', vocabulary: 'Vocabulary', reference: 'Reference', guideline: 'Guideline' }

function UploadModal({ open, onClose, onDone }) {
  const [f, setF] = useState({ title: '', source: '', language: 'en', doc_type: 'reference', text: '' })
  const [file, setFile] = useState(null)
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setErr('')
    if (!f.title.trim()) return setErr('Please add a title.')
    if (!file && !f.text.trim()) return setErr('Choose a file or paste text.')
    const fd = new FormData()
    Object.entries(f).forEach(([k, v]) => { if (k !== 'text' || !file) fd.append(k, v) })
    if (file) fd.append('file', file)
    setLoading(true)
    try { const r = await api('/admin/knowledge', { method: 'POST', form: fd }); onDone(r.document); setF({ title: '', source: '', language: 'en', doc_type: 'reference', text: '' }); setFile(null) }
    catch (e2) { setErr(e2.message) } finally { setLoading(false) }
  }
  return (
    <Modal open={open} onClose={onClose} title="Add knowledge-base document" wide>
      <form onSubmit={submit} className="space-y-4">
        {err && <Alert tone="error">{err}</Alert>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Title" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} />
          <Input label="Source / reference" placeholder="Book, website or author" value={f.source} onChange={e => setF({ ...f, source: e.target.value })} />
          <Select label="Language" value={f.language} onChange={e => setF({ ...f, language: e.target.value })}><option value="en">English</option><option value="fil">Filipino</option><option value="any">Both / any</option></Select>
          <Select label="Document type" value={f.doc_type} onChange={e => setF({ ...f, doc_type: e.target.value })}>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
        </div>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-ink-300">File (.txt, .md, .csv, .pdf — max 10 MB)</label>
          <input type="file" accept=".txt,.md,.markdown,.csv,.pdf" onChange={e => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-ink-300 file:mr-3 file:rounded-lg file:border-0 file:bg-ink-700 file:px-3 file:py-2 file:text-ink-100 hover:file:bg-ink-600" />
        </div>
        {!file && <Textarea label="…or paste text" className="min-h-40 font-mono text-xs" value={f.text} onChange={e => setF({ ...f, text: e.target.value })} />}
        <p className="text-xs text-ink-400">The document is split into chunks, embedded and added to the vector store immediately. Only upload material you have the right to use, and cite its source.</p>
        <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={onClose}>Cancel</Button><Button type="submit" icon={Upload} loading={loading}>Upload & process</Button></div>
      </form>
    </Modal>
  )
}

function DocModal({ id, onClose, onSaved }) {
  const { data } = useApi(`/admin/knowledge/${id}`)
  const [edit, setEdit] = useState(null)
  const [saving, setSaving] = useState(false)
  const d = data?.document
  const save = async () => {
    setSaving(true)
    try { const r = await api(`/admin/knowledge/${id}`, { method: 'PATCH', body: edit }); onSaved(r.document); onClose() } finally { setSaving(false) }
  }
  return (
    <Modal open onClose={onClose} title={d?.title || 'Document'} wide
      footer={edit ? <><Button variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button loading={saving} onClick={save}>Save & reprocess</Button></>
        : d && <Button variant="secondary" onClick={() => setEdit({ title: d.title, source: d.source || '', language: d.language, doc_type: d.doc_type, content: d.content })}>Edit</Button>}>
      {!d ? <Spinner /> : edit ? (
        <div className="space-y-3">
          <Input label="Title" value={edit.title} onChange={e => setEdit({ ...edit, title: e.target.value })} />
          <Input label="Source" value={edit.source} onChange={e => setEdit({ ...edit, source: e.target.value })} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label="Language" value={edit.language} onChange={e => setEdit({ ...edit, language: e.target.value })}><option value="en">English</option><option value="fil">Filipino</option><option value="any">Both / any</option></Select>
            <Select label="Type" value={edit.doc_type} onChange={e => setEdit({ ...edit, doc_type: e.target.value })}>{Object.entries(TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
          </div>
          <Textarea label="Content" className="min-h-72 font-mono text-xs" value={edit.content} onChange={e => setEdit({ ...edit, content: e.target.value })} />
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <div className="flex flex-wrap gap-2"><Badge tone={STATUS[d.status]}>{d.status}</Badge><Badge>{TYPES[d.doc_type]}</Badge><Badge>{d.language}</Badge><Badge>{d.chunk_count} chunks</Badge></div>
          <p className="text-xs text-ink-400">Source: {d.source || '—'}</p>
          {d.error && <Alert tone="error">{d.error}</Alert>}
          <pre className="scroll-thin max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-xl bg-ink-900 p-4 font-sans text-xs text-ink-300">{d.content}</pre>
        </div>
      )}
    </Modal>
  )
}

function SearchTest() {
  const [q, setQ] = useState('lungkot pag-asa tanaga')
  const [type, setType] = useState('')
  const [res, setRes] = useState(null)
  const [loading, setLoading] = useState(false)
  const run = async (e) => { e.preventDefault(); setLoading(true); try { setRes(await api('/admin/knowledge/search-test', { method: 'POST', body: { query: q, source_type: type || null, k: 6 } })) } finally { setLoading(false) } }
  return (
    <Card className="p-5">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold"><FlaskConical className="h-4 w-4 text-iris-400" /> Retrieval test</h2>
      <form onSubmit={run} className="flex flex-wrap gap-2">
        <input value={q} onChange={e => setQ(e.target.value)} aria-label="Test query" className="focus-ring min-w-48 flex-1 rounded-xl border border-ink-600 bg-ink-900 px-3 py-2 text-sm" />
        <select value={type} onChange={e => setType(e.target.value)} aria-label="Source type" className="focus-ring rounded-xl border border-ink-600 bg-ink-900 px-3 py-2 text-sm">
          <option value="">All sources</option><option value="document">Documents</option><option value="dictionary">Dictionary</option><option value="form">Poetry forms</option>
        </select>
        <Button type="submit" loading={loading}>Search</Button>
      </form>
      {res && (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-ink-400">{res.hits.length} results in {res.latency_ms} ms</p>
          {res.hits.map((h, i) => (
            <div key={i} className="rounded-xl border border-ink-700 bg-ink-900/60 p-3 text-xs">
              <div className="mb-1 flex gap-1.5"><Badge tone="iris">{h.score}</Badge><Badge>{h.source_type}</Badge><Badge>{h.language}</Badge>{h.category && <Badge>{h.category}</Badge>}</div>
              <p className="text-ink-300">{h.text}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function RagLogs() {
  const [onlyErr, setOnlyErr] = useState(false)
  const { data } = useApi(`/admin/rag-logs${qs({ only_errors: onlyErr || undefined, limit: 50 })}`, [onlyErr])
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold">Retrieval & generation activity</h2>
        <label className="flex items-center gap-2 text-xs text-ink-300"><input type="checkbox" checked={onlyErr} onChange={e => setOnlyErr(e.target.checked)} /> Errors only</label></div>
      {data?.summary_7d?.length > 0 && (
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
          {data.summary_7d.map(s => <div key={s.stage} className="rounded-lg bg-ink-800 px-3 py-2 text-xs"><p className="capitalize text-ink-400">{s.stage}</p><p className="tabular-nums">{s.count} · {s.avg_latency_ms} ms{s.avg_top_score != null && ` · top ${s.avg_top_score}`}</p></div>)}
        </div>
      )}
      <div className="scroll-thin max-h-80 overflow-y-auto">
        <table className="w-full text-left text-xs"><tbody className="divide-y divide-ink-700">
          {data?.logs?.map(l => (
            <tr key={l.id}><td className="py-1.5 pr-2 text-ink-400">{fmtDate(l.at)}</td><td className="pr-2 capitalize">{l.stage}</td>
              <td className="pr-2"><span className={l.ok ? 'text-emerald-300' : 'text-rose-300'}>{l.ok ? 'ok' : 'error'}</span></td>
              <td className="pr-2 tabular-nums">{l.latency_ms} ms</td><td className="pr-2 tabular-nums">{l.result_count ?? ''}</td><td className="text-ink-400">{l.detail}</td></tr>
          ))}
        </tbody></table>
        {data?.logs?.length === 0 && <p className="py-4 text-center text-xs text-ink-400">No activity recorded.</p>}
      </div>
    </Card>
  )
}

export default function Knowledge() {
  const toast = useToast()
  const { data, error, reload } = useApi('/admin/knowledge')
  const { data: health } = useApi('/admin/health')
  const [upload, setUpload] = useState(false)
  const [view, setView] = useState(null)
  const [del, setDel] = useState(null)
  const [busy, setBusy] = useState(null)

  const reprocess = async (d) => { setBusy(d.id); try { const r = await api(`/admin/knowledge/${d.id}/reprocess`, { method: 'POST' }); toast(r.document.status === 'ready' ? 'Document reprocessed.' : `Processing failed: ${r.document.error}`, r.document.status === 'ready' ? 'success' : 'error'); reload() } finally { setBusy(null) } }
  const reprocessAll = async () => { setBusy('all'); try { const r = await api('/admin/knowledge/reprocess-all', { method: 'POST' }); toast(`Re-embedded ${r.result.documents} documents, ${r.result.forms} forms, ${r.result.dictionary} words in ${r.seconds}s.`); reload() } catch (e) { toast(e.message, 'error') } finally { setBusy(null) } }
  const remove = async () => { await api(`/admin/knowledge/${del.id}`, { method: 'DELETE' }); toast('Document removed.'); setDel(null); reload() }
  const st = data?.stats

  return (
    <>
      <PageHeader title="AI & Knowledge Base" subtitle="Documents retrieved by the RAG pipeline before every poem."
        actions={<><Button variant="secondary" icon={RefreshCw} loading={busy === 'all'} onClick={reprocessAll}>Reprocess all</Button><Button icon={Upload} onClick={() => setUpload(true)}>Add document</Button></>} />
      {health && !health.ai.configured && <Alert tone="warn" className="mb-4" title="Language model not configured">{health.ai.setup_hint}</Alert>}
      <div className="mb-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Documents" value={data?.documents?.length} sub={`${data?.documents?.filter(d => d.status === 'error').length || 0} with errors`} />
        <Stat label="Vector chunks" value={st?.total_chunks} sub={st?.stale_chunks ? `${st.stale_chunks} stale — reprocess` : 'all current'} tone="sky" />
        <Stat label="Embedding model" value={<span className="text-base">{st?.embedding_model}</span>} sub={health?.embeddings?.provider === 'local' ? 'offline lexical' : 'remote semantic'} tone="green" />
        <Stat label="LLM" value={<span className="text-base">{health?.ai?.model}</span>} sub={health ? (health.ai.configured ? `${health.ai.provider} · ready` : 'not configured') : ''} tone="amber" />
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <Table head={['Title', 'Type', 'Language', 'Status', 'Chunks', 'Updated', '']}>
        {data?.documents?.map(d => (
          <tr key={d.id}>
            <td className="px-4 py-3"><p className="font-medium">{d.title}</p><p className="max-w-md truncate text-xs text-ink-400">{d.source || 'No source'}{d.is_system && ' · starter'}</p></td>
            <td className="px-4 py-3 text-xs">{TYPES[d.doc_type]}</td><td className="px-4 py-3 text-xs uppercase">{d.language}</td>
            <td className="px-4 py-3"><Badge tone={STATUS[d.status]}>{d.status}</Badge></td><td className="px-4 py-3 tabular-nums">{d.chunk_count}</td>
            <td className="px-4 py-3 text-xs text-ink-400">{fmtDate(d.processed_at || d.uploaded_at)}</td>
            <td className="px-4 py-3"><div className="flex justify-end">
              <IconButton label="View / edit" icon={Eye} onClick={() => setView(d.id)} />
              <IconButton label="Reprocess" icon={RefreshCw} className={cx(busy === d.id && 'animate-spin')} onClick={() => reprocess(d)} />
              <IconButton label="Delete" icon={Trash2} className="hover:text-rose-300" onClick={() => setDel(d)} />
            </div></td>
          </tr>
        ))}
      </Table>
      <div className="mt-5 grid gap-5 lg:grid-cols-2"><SearchTest /><RagLogs /></div>
      <UploadModal open={upload} onClose={() => setUpload(false)} onDone={(d) => { setUpload(false); toast(d.status === 'ready' ? `Added “${d.title}” (${d.chunk_count} chunks).` : `Upload saved but processing failed: ${d.error}`, d.status === 'ready' ? 'success' : 'error'); reload() }} />
      {view && <DocModal id={view} onClose={() => setView(null)} onSaved={() => { toast('Document updated and re-embedded.'); reload() }} />}
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} onConfirm={remove} title="Remove document?" message={`“${del?.title}” and its vectors will be removed from the knowledge base.`} />
    </>
  )
}
