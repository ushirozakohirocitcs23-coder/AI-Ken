import { useState } from 'react'
import { CheckCircle2, Pencil, Plus, Search, Trash2 } from 'lucide-react'
import { api, qs } from '../../api'
import { Alert, Badge, Button, ConfirmDialog, IconButton, Input, Modal, PageHeader, Select, Textarea, Toggle, useToast } from '../../components/ui'
import { Pager, Table, useApi } from './common'

const EMOTIONS = ['', 'happiness', 'sadness', 'inspiration', 'anger', 'envy', 'love', 'loneliness', 'hope', 'fear', 'gratitude', 'regret', 'excitement', 'confusion', 'peace', 'mixed']
const BLANK = { word: '', language: 'fil', part_of_speech: '', definition: '', synonyms: '', antonyms: '', example: '', emotion_category: '', literary_usage: '', level: 'intermediate', source: '', source_url: '', verified: false }

export default function Dictionary() {
  const toast = useToast()
  const [f, setF] = useState({ q: '', language: '', verified: '', page: 1 })
  const { data, error, reload } = useApi(`/admin/dictionary${qs({ ...f, per_page: 20 })}`, [f])
  const [edit, setEdit] = useState(null)
  const [del, setDel] = useState(null)
  const [err, setErr] = useState('')

  const open = (e) => { setErr(''); setEdit(e ? { ...BLANK, ...e, synonyms: (e.synonyms || []).join(', '), antonyms: (e.antonyms || []).join(', '), emotion_category: e.emotion_category || '', part_of_speech: e.part_of_speech || '', example: e.example || '', literary_usage: e.literary_usage || '', source_url: e.source_url || '' } : { ...BLANK }) }
  const save = async () => {
    setErr('')
    const split = s => s.split(',').map(x => x.trim()).filter(Boolean)
    const body = { ...edit, synonyms: split(edit.synonyms), antonyms: split(edit.antonyms), emotion_category: edit.emotion_category || null,
      part_of_speech: edit.part_of_speech || null, example: edit.example || null, literary_usage: edit.literary_usage || null, source_url: edit.source_url || null }
    delete body.id; delete body.provenance
    try {
      await api(edit.id ? `/admin/dictionary/${edit.id}` : '/admin/dictionary', { method: edit.id ? 'PUT' : 'POST', body })
      toast(edit.id ? 'Entry updated.' : 'Entry added.'); setEdit(null); reload()
    } catch (e) { setErr(e.message) }
  }
  const verify = async (e) => {
    const body = { ...e, verified: !e.verified }
    delete body.id; delete body.provenance
    await api(`/admin/dictionary/${e.id}`, { method: 'PUT', body }); reload()
  }
  const remove = async () => { await api(`/admin/dictionary/${del.id}`, { method: 'DELETE' }); toast('Entry deleted.'); setDel(null); reload() }
  const set = k => e => setEdit({ ...edit, [k]: e.target.value })

  return (
    <>
      <PageHeader title="Dictionary & Vocabulary" subtitle="Words retrieved for poems and vocabulary explanations. Mark entries verified only after checking an authoritative source."
        actions={<Button icon={Plus} onClick={() => open(null)}>Add word</Button>} />
      <Alert tone="info" className="mb-4">Starter entries are labeled <b>pending review</b>. Users see each entry's source and verification status. English words not found here are fetched from the Free Dictionary API (when reachable) and cached with their source.</Alert>
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_160px_180px]">
        <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
          <input value={f.q} onChange={e => setF({ ...f, q: e.target.value, page: 1 })} placeholder="Search words or definitions" aria-label="Search dictionary" className="focus-ring w-full rounded-xl border border-ink-600 bg-ink-850 py-2.5 pl-9 pr-3 text-sm" /></div>
        <Select aria-label="Language" value={f.language} onChange={e => setF({ ...f, language: e.target.value, page: 1 })}><option value="">All languages</option><option value="fil">Filipino</option><option value="en">English</option></Select>
        <Select aria-label="Verification" value={f.verified} onChange={e => setF({ ...f, verified: e.target.value, page: 1 })}><option value="">Any status</option><option value="true">Verified</option><option value="false">Pending review</option></Select>
      </div>
      {error && <Alert tone="error">{error}</Alert>}
      <Table head={['Word', 'Definition', 'Emotion', 'Level', 'Source', 'Status', '']}>
        {data?.entries?.map(e => (
          <tr key={e.id} className="align-top">
            <td className="px-4 py-3"><p className="font-serif font-semibold">{e.word}</p><p className="text-xs text-ink-400">{e.language === 'fil' ? 'Filipino' : 'English'} · {e.part_of_speech}</p></td>
            <td className="max-w-sm px-4 py-3 text-xs text-ink-300">{e.definition}</td>
            <td className="px-4 py-3 text-xs capitalize">{e.emotion_category || '—'}</td><td className="px-4 py-3 text-xs capitalize">{e.level}</td>
            <td className="max-w-[180px] px-4 py-3 text-xs text-ink-400">{e.source}</td>
            <td className="px-4 py-3"><button onClick={() => verify(e)} className="focus-ring rounded-full" title="Toggle verification"><Badge tone={e.verified ? 'green' : 'neutral'}>{e.verified ? <><CheckCircle2 className="h-3 w-3" /> Verified</> : 'Pending'}</Badge></button></td>
            <td className="px-4 py-3"><div className="flex"><IconButton label="Edit" icon={Pencil} onClick={() => open(e)} /><IconButton label="Delete" icon={Trash2} className="hover:text-rose-300" onClick={() => setDel(e)} /></div></td>
          </tr>
        ))}
      </Table>
      {data && <Pager page={data.page} total={data.total} perPage={data.per_page} onPage={p => setF({ ...f, page: p })} />}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={edit?.id ? `Edit “${edit.word}”` : 'Add dictionary entry'} wide
        footer={<><Button variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={save}>Save</Button></>}>
        {edit && <div className="space-y-3">
          {err && <Alert tone="error">{err}</Alert>}
          <div className="grid gap-3 sm:grid-cols-3">
            <Input label="Word" value={edit.word} onChange={set('word')} />
            <Select label="Language" value={edit.language} onChange={set('language')}><option value="fil">Filipino</option><option value="en">English</option></Select>
            <Input label="Part of speech" value={edit.part_of_speech} onChange={set('part_of_speech')} />
          </div>
          <Textarea label="Definition" value={edit.definition} onChange={set('definition')} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Synonyms (comma-separated)" value={edit.synonyms} onChange={set('synonyms')} />
            <Input label="Antonyms (comma-separated)" value={edit.antonyms} onChange={set('antonyms')} />
          </div>
          <Input label="Example sentence" value={edit.example} onChange={set('example')} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Select label="Emotional category" value={edit.emotion_category} onChange={set('emotion_category')}>{EMOTIONS.map(x => <option key={x} value={x}>{x || '— none —'}</option>)}</Select>
            <Select label="Vocabulary level" value={edit.level} onChange={set('level')}><option value="simple">Simple</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></Select>
          </div>
          <Input label="Literary usage (optional)" value={edit.literary_usage} onChange={set('literary_usage')} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Source / reference" placeholder="e.g. UP Diksiyonaryong Filipino, p. 123" value={edit.source} onChange={set('source')} />
            <Input label="Source URL (optional)" value={edit.source_url} onChange={set('source_url')} />
          </div>
          <Toggle checked={edit.verified} onChange={v => setEdit({ ...edit, verified: v })} label="Verified" description="Only enable after checking the definition against the cited source." />
        </div>}
      </Modal>
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} onConfirm={remove} title="Delete entry?" message={`“${del?.word}” will be removed from the dictionary and vector index.`} />
    </>
  )
}
