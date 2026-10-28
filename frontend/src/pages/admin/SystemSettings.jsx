import { useEffect, useState } from 'react'
import { api } from '../../api'
import { Alert, Badge, Button, Card, Input, PageHeader, Spinner, Toggle, useToast } from '../../components/ui'
import { useApi } from './common'

const LANGS = [['fil', 'Filipino'], ['en', 'English'], ['taglish', 'Taglish']]

export default function SystemSettings() {
  const toast = useToast()
  const { data } = useApi('/admin/settings')
  const { data: h, reload: reloadHealth } = useApi('/admin/health')
  const [s, setS] = useState(null)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState('')
  useEffect(() => { if (data) setS(data.settings) }, [data])

  const save = async () => {
    setSaving(true); setErr('')
    try { setS((await api('/admin/settings', { method: 'PUT', body: { values: s } })).settings); toast('Settings saved.') }
    catch (e) { setErr(e.message) } finally { setSaving(false) }
  }
  const num = (k) => (e) => setS({ ...s, [k]: e.target.value === '' ? '' : Number(e.target.value) })
  const d = data?.descriptions || {}

  return (
    <>
      <PageHeader title="System Settings" subtitle="Generation limits, languages and platform options." actions={<Button loading={saving} onClick={save} disabled={!s}>Save settings</Button>} />
      {err && <Alert tone="error" className="mb-4">{err}</Alert>}
      {!s ? <Spinner /> : (
        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="space-y-5 p-5">
            <h2 className="font-semibold">Generation</h2>
            <Input label="Daily poem limit per user" type="number" min={0} value={s.daily_generation_limit} onChange={num('daily_generation_limit')} hint={d.daily_generation_limit} />
            <Input label="Max revision attempts" type="number" min={0} max={4} value={s.max_revision_attempts} onChange={num('max_revision_attempts')} hint={d.max_revision_attempts} />
            <Input label="Retrieved chunks per poem (top-k)" type="number" min={1} max={20} value={s.retrieval_top_k} onChange={num('retrieval_top_k')} hint={d.retrieval_top_k} />
            <Input label="Maximum story length (characters)" type="number" min={200} max={20000} value={s.max_story_chars} onChange={num('max_story_chars')} hint={d.max_story_chars} />
          </Card>
          <Card className="space-y-5 p-5">
            <h2 className="font-semibold">Languages & access</h2>
            <div>
              <p className="mb-2 text-sm font-medium text-ink-300">Supported output languages</p>
              <div className="flex flex-wrap gap-2">{LANGS.map(([k, label]) => {
                const on = s.enabled_languages.includes(k)
                return <button key={k} type="button" aria-pressed={on} onClick={() => setS({ ...s, enabled_languages: on ? s.enabled_languages.filter(x => x !== k) : [...s.enabled_languages, k] })}
                  className={`focus-ring rounded-full border px-3 py-1.5 text-sm ${on ? 'border-iris-400 bg-iris-500/20 text-iris-200' : 'border-ink-600 text-ink-400'}`}>{label}</button>
              })}</div>
              <p className="mt-1.5 text-xs text-ink-400">Poem types are enabled per form in Poetry Forms.</p>
            </div>
            <Toggle checked={s.registration_open} onChange={v => setS({ ...s, registration_open: v })} label="Open registration" description={d.registration_open} />
            <Toggle checked={s.show_word_of_day} onChange={v => setS({ ...s, show_word_of_day: v })} label="Vocabulary of the Day" description={d.show_word_of_day} />
          </Card>
          <Card className="p-5 lg:col-span-2">
            <div className="mb-3 flex items-center justify-between"><h2 className="font-semibold">System health</h2><Button size="sm" variant="secondary" onClick={reloadHealth}>Refresh</Button></div>
            {!h ? <Spinner /> : (
              <div className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl bg-ink-800 p-3"><p className="text-xs text-ink-400">Language model</p><p className="mt-1">{h.ai.provider} · {h.ai.model}</p><Badge tone={h.ai.configured ? 'green' : 'red'} className="mt-2">{h.ai.configured ? 'Configured' : 'Not configured'}</Badge>{h.ai.setup_hint && <p className="mt-1 text-xs text-amber-200">{h.ai.setup_hint}</p>}</div>
                <div className="rounded-xl bg-ink-800 p-3"><p className="text-xs text-ink-400">Embeddings</p><p className="mt-1 break-all">{h.embeddings.model}</p><p className="mt-1 text-xs text-ink-400">{h.embeddings.note}</p></div>
                <div className="rounded-xl bg-ink-800 p-3"><p className="text-xs text-ink-400">Vector store</p><p className="mt-1">{h.vector_store.chunks_current_model} chunks · {h.vector_store.probe_ms} ms probe</p><Badge tone={h.vector_store.ok ? 'green' : 'red'} className="mt-2">{h.vector_store.ok ? 'Healthy' : 'Needs reprocessing'}</Badge></div>
                <div className="rounded-xl bg-ink-800 p-3"><p className="text-xs text-ink-400">Pipeline (24h)</p>{Object.entries(h.pipeline_24h).map(([k, v]) => <p key={k} className="text-xs capitalize">{k}: {v.last_24h} {v.failed > 0 && <span className="text-rose-300">({v.failed} failed)</span>}</p>)}</div>
              </div>
            )}
            <p className="mt-3 text-xs text-ink-400">API keys and secrets are configured only in the server's <code>.env</code> file and are never shown in the browser.</p>
          </Card>
        </div>
      )}
    </>
  )
}
