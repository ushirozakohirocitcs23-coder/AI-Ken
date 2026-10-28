import { useState } from 'react'
import { Pencil } from 'lucide-react'
import { api } from '../../api'
import { Alert, Badge, Button, Card, Input, Modal, PageHeader, Spinner, Textarea, Toggle, useToast } from '../../components/ui'
import { useApi } from './common'

function ruleSummary(r) {
  const out = []
  if (r.lines) out.push(`${r.lines} lines`)
  else if (r.lines_min) out.push(`${r.lines_min}–${r.lines_max} lines`)
  if (r.lines_multiple_of) out.push(`${r.lines_multiple_of}-line stanzas`)
  if (r.syllables) out.push(`${r.syllables.join('-')} syllables`)
  if (r.syllables_per_line) out.push(`${r.syllables_per_line} syll./line${r.syllable_mode === 'approximate' ? ' (approx.)' : ''}`)
  if (r.rhyme) out.push(r.rhyme)
  if (r.words_per_line) out.push(`words ${r.words_per_line.join('-')}`)
  if (r.acrostic) out.push('acrostic')
  return out.join(' · ') || 'flexible'
}

export default function Forms() {
  const toast = useToast()
  const { data, error, reload } = useApi('/admin/forms')
  const [edit, setEdit] = useState(null)
  const [err, setErr] = useState('')

  const toggle = async (f) => { await api(`/admin/forms/${f.id}`, { method: 'PATCH', body: { enabled: !f.enabled } }); toast(`${f.name} ${f.enabled ? 'disabled' : 'enabled'}.`); reload() }
  const save = async () => {
    setErr('')
    let rules
    try { rules = JSON.parse(edit.rulesText) } catch { return setErr('Rules must be valid JSON.') }
    try {
      await api(`/admin/forms/${edit.id}`, { method: 'PATCH', body: { name: edit.name, description: edit.description, guidance: edit.guidance, source_references: edit.source_references, rules } })
      toast('Form updated and re-indexed.'); setEdit(null); reload()
    } catch (e) { setErr(e.message) }
  }

  return (
    <>
      <PageHeader title="Poetry Forms & Rules" subtitle="Structures the validator checks and the rules retrieved before generation." />
      {error && <Alert tone="error">{error}</Alert>}
      {!data ? <Spinner /> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.forms.map(f => (
            <Card key={f.id} className="flex flex-col p-4">
              <div className="flex items-start justify-between gap-2">
                <div><p className="font-semibold">{f.name}</p><p className="text-xs text-ink-400">{f.key}</p></div>
                <Toggle checked={f.enabled} onChange={() => toggle(f)} label="" />
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5"><Badge tone={f.tradition === 'traditional' ? 'amber' : f.tradition === 'adapted' ? 'blue' : 'neutral'}>{f.tradition}</Badge><Badge>{f.language === 'fil' ? 'Filipino' : 'Any language'}</Badge></div>
              <p className="mt-2 flex-1 text-sm text-ink-300">{f.description}</p>
              <p className="mt-2 rounded-lg bg-ink-900 px-2.5 py-1.5 font-mono text-[11px] text-iris-300">{ruleSummary(f.rules)}</p>
              <Button size="sm" variant="ghost" icon={Pencil} className="mt-2 self-start" onClick={() => { setErr(''); setEdit({ ...f, rulesText: JSON.stringify(f.rules, null, 2) }) }}>Edit rules</Button>
            </Card>
          ))}
        </div>
      )}
      <Modal open={!!edit} onClose={() => setEdit(null)} title={`Edit ${edit?.name}`} wide
        footer={<><Button variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={save}>Save</Button></>}>
        {edit && <div className="space-y-3">
          {err && <Alert tone="error">{err}</Alert>}
          <Input label="Name" value={edit.name} onChange={e => setEdit({ ...edit, name: e.target.value })} />
          <Textarea label="Description (shown to users)" value={edit.description} onChange={e => setEdit({ ...edit, description: e.target.value })} />
          <Textarea label="Generation guidance (retrieved into the AI prompt)" className="min-h-32" value={edit.guidance} onChange={e => setEdit({ ...edit, guidance: e.target.value })} />
          <Textarea label="Machine-checkable rules (JSON)" className="min-h-56 font-mono text-xs" value={edit.rulesText} onChange={e => setEdit({ ...edit, rulesText: e.target.value })}
            hint="Keys: lines, lines_min, lines_max, lines_multiple_of, syllables, syllables_per_line, syllable_tolerance, syllable_mode, rhyme, rhyme_alternatives, rhyme_repeat, rhyme_per_stanza, words_per_line, stanza_size, locked, controls." />
          <Textarea label="Source references" value={edit.source_references || ''} onChange={e => setEdit({ ...edit, source_references: e.target.value })} />
        </div>}
      </Modal>
    </>
  )
}
