import { useEffect, useState } from 'react'
import { AlertTriangle, BookOpen, Bookmark, BookmarkCheck, CheckCircle2, ClipboardCheck, Copy, HelpCircle, Languages,
  LifeBuoy, RefreshCw, Search, Shapes, Star, XCircle } from 'lucide-react'
import { api } from '../../api'
import { Alert, Badge, Button, IconButton, Input, Modal, Spinner, Textarea, cx, useToast } from '../../components/ui'
import PoemSettingsPanel, { DEFAULT_SETTINGS } from './PoemSettings'

const LANG = { fil: 'Filipino', en: 'English', taglish: 'Taglish' }
const STATUS = {
  pass: ['green', CheckCircle2, 'Verified'], pass_estimate: ['blue', HelpCircle, 'Passed · estimates'],
  fail: ['amber', AlertTriangle, 'Adaptation'], info: ['neutral', null, ''], estimate: ['blue', HelpCircle, 'Estimate'],
}

export function ValidationReport({ v }) {
  if (!v?.checks) return null
  return (
    <div className="space-y-3 text-sm">
      <p className="font-medium">{v.status_label}</p>
      <div className="overflow-x-auto rounded-xl border border-ink-700">
        <table className="w-full text-left text-xs">
          <thead className="bg-ink-800 text-ink-400"><tr><th className="px-3 py-2 font-medium">Check</th><th className="px-3 py-2 font-medium">Required</th><th className="px-3 py-2 font-medium">Actual</th><th className="px-3 py-2 font-medium">Result</th></tr></thead>
          <tbody>
            <tr className="border-t border-ink-700"><td className="px-3 py-2">Poem type</td><td className="px-3 py-2" colSpan={2}>{v.form_name} <span className="text-ink-400">({v.tradition})</span></td><td /></tr>
            <tr className="border-t border-ink-700"><td className="px-3 py-2">Language</td><td className="px-3 py-2" colSpan={2}>{LANG[v.language] || v.language}</td><td /></tr>
            {v.checks.map(c => {
              const [tone, Icon] = STATUS[c.status] || STATUS.info
              return (
                <tr key={c.name} className="border-t border-ink-700 align-top">
                  <td className="px-3 py-2">{c.name}</td><td className="px-3 py-2 text-ink-300">{String(c.required)}</td>
                  <td className="px-3 py-2 text-ink-300">{String(c.actual)}{c.detail && c.status !== 'pass' && <span className="mt-0.5 block text-[11px] text-ink-400">{c.detail}</span>}</td>
                  <td className="px-3 py-2">{c.status === 'info' ? <span className="text-ink-400">—</span> :
                    <span className={cx('inline-flex items-center gap-1', tone === 'green' ? 'text-emerald-300' : tone === 'blue' ? 'text-sky-300' : 'text-amber-300')}>
                      {c.status === 'fail' ? <XCircle className="h-3.5 w-3.5" /> : Icon && <Icon className="h-3.5 w-3.5" />}{c.status === 'pass' ? 'Pass' : c.status === 'fail' ? 'Fail' : 'Estimate'}</span>}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {v.lines?.some(l => 'target' in l) && (
        <details className="rounded-xl border border-ink-700 px-3 py-2">
          <summary className="cursor-pointer text-xs text-ink-300">Syllables per line</summary>
          <ol className="mt-2 space-y-1 text-xs">
            {v.lines.map(l => (
              <li key={l.line} className="flex gap-2"><span className={cx('w-12 shrink-0 tabular-nums', l.ok === false ? 'text-amber-300' : 'text-emerald-300')}>{l.syllables}/{l.target}</span>
                <span className="text-ink-300">{l.words.map(w => `${w.w}(${w.s})`).join(' ')}</span></li>
            ))}
          </ol>
        </details>
      )}
      {v.detected_rhyme_scheme && <p className="text-xs text-ink-400">Detected end-rhyme pattern: <span className="font-mono text-ink-300">{v.detected_rhyme_scheme}</span></p>}
      {v.notes?.length > 0 && <ul className="list-disc space-y-0.5 pl-5 text-xs text-ink-400">{v.notes.map(n => <li key={n}>{n}</li>)}</ul>}
      <p className="text-[11px] text-ink-400">Syllables use the CMU Pronouncing Dictionary for English and Filipino vowel-based counting (bawat patinig = isang pantig). Rhymes are judged by pronunciation or traditional tugma groups; items marked "estimate" deserve a quick manual check.</p>
    </div>
  )
}

export function VocabEntry({ e }) {
  const prov = e.provenance === 'verified' ? ['green', 'Verified source'] : e.provenance === 'ai_generated' ? ['amber', 'AI-generated · unverified'] : ['neutral', 'Curated · pending review']
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-900/50 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-serif text-base font-semibold">{e.word}</span>
        {e.part_of_speech && <span className="text-xs italic text-ink-400">{e.part_of_speech}</span>}
        <Badge>{LANG[e.language] || e.language}</Badge><Badge tone={prov[0]}>{prov[1]}</Badge>
      </div>
      <p className="mt-1 text-sm text-ink-200">{e.definition}</p>
      {e.example && <p className="mt-1 text-xs italic text-ink-400">“{e.example}”</p>}
      {(e.synonyms?.length > 0 || e.antonyms?.length > 0) && (
        <p className="mt-1.5 text-xs text-ink-400">
          {e.synonyms?.length > 0 && <>Synonyms: <span className="text-ink-300">{e.synonyms.join(', ')}</span>. </>}
          {e.antonyms?.length > 0 && <>Antonyms: <span className="text-ink-300">{e.antonyms.join(', ')}</span>.</>}
        </p>
      )}
      <p className="mt-1.5 text-[11px] text-ink-400">Source: {e.source_url ? <a className="underline" href={e.source_url} target="_blank" rel="noreferrer">{e.source}</a> : e.source}</p>
    </div>
  )
}

function WordLookup({ language, context }) {
  const [word, setWord] = useState('')
  const [res, setRes] = useState(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const run = async (ai = false) => {
    if (!word.trim()) return
    setLoading(true); setErr('')
    try {
      const r = await api(`/dictionary/lookup?word=${encodeURIComponent(word.trim())}&language=${language}${ai ? `&ai=true&context=${encodeURIComponent(context.slice(0, 300))}` : ''}`)
      setRes(r)
    } catch (e) { setErr(e.message) } finally { setLoading(false) }
  }
  return (
    <div className="space-y-2">
      <form className="flex gap-2" onSubmit={e => { e.preventDefault(); run() }}>
        <div className="flex-1"><Input aria-label="Look up a word" placeholder="Look up another word…" value={word} onChange={e => { setWord(e.target.value); setRes(null) }} /></div>
        <Button type="submit" variant="secondary" icon={Search} loading={loading}>Look up</Button>
      </form>
      {err && <Alert tone="error">{err}</Alert>}
      {res?.entry && <VocabEntry e={res.entry} />}
      {res && !res.entry && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-ink-300">No dictionary entry found.
          <Button size="sm" variant="subtle" onClick={() => run(true)}>Ask AI-KEN (unverified)</Button></div>
      )}
    </div>
  )
}

function Stars({ value, onRate }) {
  const [hover, setHover] = useState(0)
  return (
    <div className="flex" role="radiogroup" aria-label="Rate this poem" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map(n => (
        <button key={n} type="button" role="radio" aria-checked={value === n} aria-label={`${n} star${n > 1 ? 's' : ''}`}
          onMouseEnter={() => setHover(n)} onClick={() => onRate(n)} className="focus-ring rounded p-0.5">
          <Star className={cx('h-4 w-4', (hover || value) >= n ? 'fill-amber-300 text-amber-300' : 'text-ink-400')} />
        </button>
      ))}
    </div>
  )
}

export default function PoemCard({ poem, onUpdate, onNewMessage, busy, setBusy }) {
  const toast = useToast()
  const [panel, setPanel] = useState(null) // vocab | report | feedback
  const [restructure, setRestructure] = useState(false)
  const [rs, setRs] = useState(null)
  const [comment, setComment] = useState(poem.feedback?.comments || '')
  const [action, setAction] = useState(null)
  const v = poem.validation || {}
  const [tone, Icon, label] = STATUS[v.overall] || STATUS.info
  const emotions = poem.detected_emotions || []
  const supportNote = poem.analysis?.support_note

  const copy = async () => {
    try { await navigator.clipboard.writeText(`${poem.title}\n\n${poem.content}`); toast('Poem copied to clipboard.') }
    catch { toast('Copy failed — select the text and copy manually.', 'error') }
  }
  const save = async () => {
    const r = await api(`/poems/${poem.id}`, { method: 'PATCH', body: { is_saved: !poem.is_saved } })
    onUpdate?.(r.poem); toast(r.poem.is_saved ? 'Saved to My Saved Poems.' : 'Removed from saved poems.')
  }
  const doAction = async (name, fn) => {
    setAction(name); setBusy?.(true)
    try { onNewMessage?.((await fn()).message) }
    catch (e) { toast(e.detail?.message || e.message, 'error') }
    finally { setAction(null); setBusy?.(false) }
  }
  const regenerate = () => doAction('regen', () => api(`/poems/${poem.id}/regenerate`, { method: 'POST', body: {} }))
  const translate = (target) => doAction(`tr-${target}`, () => api(`/poems/${poem.id}/translate`, { method: 'POST', body: { target } }))
  const applyStructure = () => { setRestructure(false); doAction('restructure', () => api(`/poems/${poem.id}/regenerate`, { method: 'POST', body: { settings: rs } })) }
  const rate = async (rating, comments = comment) => {
    const r = await api(`/poems/${poem.id}/feedback`, { method: 'POST', body: { rating, comments: comments || null } })
    onUpdate?.({ ...poem, feedback: r.feedback }); toast(r.message)
  }
  const disabled = busy || !!action

  return (
    <article className="rise rounded-2xl border border-ink-700 bg-ink-850 shadow-lg shadow-black/20">
      <header className="flex flex-wrap items-start justify-between gap-2 px-5 pt-5">
        <div className="min-w-0">
          <h3 className="font-serif text-xl font-semibold leading-tight">{poem.title}</h3>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            <Badge tone="iris">{v.form_name || poem.poem_type}</Badge><Badge>{LANG[poem.language]}</Badge>
            {poem.kind !== 'original' && <Badge tone="blue">{poem.kind === 'translation' ? 'Translation' : 'New version'}</Badge>}
            {v.overall && <button onClick={() => setPanel(panel === 'report' ? null : 'report')} className="focus-ring rounded-full">
              <Badge tone={tone}>{Icon && <Icon className="h-3 w-3" />}{label}</Badge></button>}
          </div>
        </div>
        <div className="flex">
          <IconButton label="Copy poem" icon={Copy} onClick={copy} />
          <IconButton label={poem.is_saved ? 'Unsave poem' : 'Save poem'} icon={poem.is_saved ? BookmarkCheck : Bookmark} active={poem.is_saved} onClick={save} />
        </div>
      </header>

      <div className="px-5 py-4"><p className="poem-text text-[16.5px] text-ink-100">{poem.content}</p></div>

      {supportNote && <div className="px-5 pb-3"><Alert tone="info" title="You're not alone"><span className="inline-flex items-start gap-1"><LifeBuoy className="mt-0.5 h-3.5 w-3.5 shrink-0" />{supportNote}</span></Alert></div>}

      {emotions.length > 0 && (
        <div className="px-5 pb-3">
          <p className="text-xs text-ink-400">Emotions AI-KEN noticed in your words <span className="italic">(an interpretation, not a diagnosis)</span>:</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">{emotions.map((e, i) => <Badge key={i} tone="neutral" className="capitalize">{e.label || e.emotion}</Badge>)}</div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5 border-t border-ink-700 px-4 py-2.5">
        <Button size="sm" variant="ghost" icon={RefreshCw} loading={action === 'regen'} disabled={disabled} onClick={regenerate}>Regenerate</Button>
        <Button size="sm" variant="ghost" icon={Shapes} loading={action === 'restructure'} disabled={disabled}
          onClick={() => { setRs({ ...DEFAULT_SETTINGS, ...(poem.settings || {}), poem_type: poem.poem_type, language: poem.language }); setRestructure(true) }}>Change structure</Button>
        {['fil', 'en'].filter(l => l !== poem.language).map(l => (
          <Button key={l} size="sm" variant="ghost" icon={Languages} loading={action === `tr-${l}`} disabled={disabled} onClick={() => translate(l)}>To {LANG[l]}</Button>
        ))}
        <Button size="sm" variant={panel === 'vocab' ? 'subtle' : 'ghost'} icon={BookOpen} onClick={() => setPanel(panel === 'vocab' ? null : 'vocab')}>Vocabulary</Button>
        <Button size="sm" variant={panel === 'report' ? 'subtle' : 'ghost'} icon={ClipboardCheck} onClick={() => setPanel(panel === 'report' ? null : 'report')}>Validation</Button>
        <div className="ml-auto flex items-center gap-2">
          <Stars value={poem.feedback?.rating || 0} onRate={(n) => { rate(n); setPanel('feedback') }} />
        </div>
      </div>

      {panel && (
        <div className="border-t border-ink-700 px-5 py-4">
          {panel === 'report' && <ValidationReport v={v} />}
          {panel === 'vocab' && (
            <div className="space-y-2">
              {poem.vocabulary?.length ? poem.vocabulary.map(e => <VocabEntry key={e.word} e={e} />) : <p className="text-sm text-ink-400">No highlighted vocabulary for this poem.</p>}
              <WordLookup language={poem.language} context={poem.content} />
            </div>
          )}
          {panel === 'feedback' && (
            <form className="space-y-2" onSubmit={e => { e.preventDefault(); rate(poem.feedback?.rating || 5, comment); setPanel(null) }}>
              <Textarea label="Any suggestions? (optional)" value={comment} maxLength={1000} onChange={e => setComment(e.target.value)} className="min-h-20" />
              <div className="flex justify-end gap-2"><Button size="sm" variant="ghost" type="button" onClick={() => setPanel(null)}>Close</Button><Button size="sm" type="submit">Send feedback</Button></div>
            </form>
          )}
        </div>
      )}

      <Modal open={restructure} onClose={() => setRestructure(false)} title="Rewrite with a different structure" wide
        footer={<><Button variant="secondary" onClick={() => setRestructure(false)}>Cancel</Button><Button onClick={applyStructure}>Rewrite poem</Button></>}>
        {rs && <PoemSettingsPanel value={rs} onChange={setRs} />}
      </Modal>
    </article>
  )
}

export function WritingIndicator() {
  const steps = ['Reading your story', 'Sensing the emotions', 'Retrieving poetry rules & vocabulary', 'Writing your poem', 'Checking structure']
  const [i, setI] = useState(0)
  useEffect(() => { const t = setInterval(() => setI(x => Math.min(x + 1, steps.length - 1)), 2200); return () => clearInterval(t) }, [steps.length])
  return (
    <div className="rise flex items-center gap-3 rounded-2xl border border-ink-700 bg-ink-850 px-4 py-3 text-sm text-ink-300" role="status" aria-live="polite">
      <Spinner className="h-4 w-4" /> <span>{steps[i]}…</span>
    </div>
  )
}
