import { useEffect, useState } from 'react'
import { api } from '../../api'
import { Badge, Input, Select, Toggle, cx } from '../../components/ui'

export const DEFAULT_SETTINGS = {
  language: 'auto', poem_type: 'auto', lines: null, syllable_pattern: null, rhyme_scheme: null,
  vocabulary_level: 'intermediate', emotional_tone: [], show_vocabulary: true, acrostic_word: '', traditional_meter: true,
}

let formsCache = null
export function useForms() {
  const [data, setData] = useState(formsCache)
  useEffect(() => {
    if (formsCache) return
    api('/forms').then(r => { formsCache = r; setData(r) }).catch(() => {})
  }, [])
  return data
}

const TONES = ['happiness', 'sadness', 'inspiration', 'anger', 'envy', 'love', 'hope', 'loneliness', 'gratitude', 'regret', 'mixed']
const LANG_LABEL = { fil: 'Filipino', en: 'English', taglish: 'Taglish' }

export function settingsSummary(s, forms) {
  const f = forms?.forms?.find(x => x.key === s.poem_type)
  return [s.language === 'auto' ? 'Auto language' : LANG_LABEL[s.language], f ? f.name : 'Auto form',
    s.rhyme_scheme && s.rhyme_scheme !== 'none' ? s.rhyme_scheme : null, s.lines ? `${s.lines} lines` : null,
    s.emotional_tone?.length ? s.emotional_tone.join(', ') : null].filter(Boolean)
}

export default function PoemSettingsPanel({ value, onChange, compact }) {
  const data = useForms()
  const s = value
  const set = (patch) => onChange({ ...s, ...patch })
  const form = data?.forms?.find(f => f.key === s.poem_type)
  const controls = form?.rules?.controls || {}
  const intl = data?.forms?.filter(f => f.language !== 'fil') || []
  const fil = data?.forms?.filter(f => f.language === 'fil') || []
  const langs = data?.languages || ['fil', 'en', 'taglish']

  const changeForm = (key) => set({ poem_type: key, lines: null, rhyme_scheme: null, syllable_pattern: null })
  const toggleTone = (t) => {
    const cur = s.emotional_tone || []
    set({ emotional_tone: cur.includes(t) ? cur.filter(x => x !== t) : cur.length >= 3 ? cur : [...cur, t] })
  }

  return (
    <div className={cx('space-y-4', compact && 'text-sm')}>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select label="Language" value={s.language} onChange={e => set({ language: e.target.value })}>
          <option value="auto">Automatic detection</option>
          {langs.map(l => <option key={l} value={l}>{LANG_LABEL[l]}</option>)}
        </Select>
        <Select label="Poem type" value={s.poem_type} onChange={e => changeForm(e.target.value)}>
          <option value="auto">Auto-choose structure</option>
          <optgroup label="Poetic forms">{intl.map(f => <option key={f.key} value={f.key}>{f.name}</option>)}</optgroup>
          {fil.length > 0 && <optgroup label="Filipino forms">{fil.map(f => <option key={f.key} value={f.key}>{f.name}</option>)}</optgroup>}
        </Select>
      </div>
      {form && (
        <div className="rounded-xl border border-ink-700 bg-ink-900/60 px-3 py-2.5 text-xs text-ink-300">
          <div className="mb-1 flex items-center gap-2"><span className="font-semibold text-ink-100">{form.name}</span>
            <Badge tone={form.tradition === 'traditional' ? 'amber' : form.tradition === 'adapted' ? 'blue' : 'neutral'}>{form.tradition}</Badge></div>
          {form.description}
        </div>
      )}
      {s.poem_type === 'auto' && <p className="text-xs text-ink-400">AI-KEN will recommend a form that suits your story.</p>}

      <div className="grid gap-3 sm:grid-cols-2">
        {controls.lines && (
          <Select label="Number of lines" value={s.lines ?? ''} onChange={e => set({ lines: e.target.value ? Number(e.target.value) : null })}>
            <option value="">Default</option>
            {(controls.line_options || [2, 3, 4, 5, 7, 10, 14]).map(n => <option key={n} value={n}>{n}</option>)}
          </Select>
        )}
        {controls.rhyme && (
          <Select label="Rhyme scheme" value={s.rhyme_scheme ?? ''} onChange={e => set({ rhyme_scheme: e.target.value || null })}>
            <option value="">Default{form?.rules?.rhyme ? ` (${form.rules.rhyme})` : ''}</option>
            {(controls.rhyme_options || []).map(r => <option key={r} value={r}>{r === 'none' ? 'No rhyme' : r}</option>)}
          </Select>
        )}
        {controls.syllable_options && (
          <Select label="Syllable pattern" value={s.syllable_pattern ?? ''} onChange={e => set({ syllable_pattern: e.target.value || null })}>
            <option value="">Default</option>
            {controls.syllable_options.map(p => <option key={p} value={p}>{p}</option>)}
          </Select>
        )}
        {controls.custom_syllables && (
          <Input label="Syllable pattern (optional)" placeholder="e.g. 7-7-7-7" value={s.syllable_pattern ?? ''} onChange={e => set({ syllable_pattern: e.target.value || null })} />
        )}
        {controls.acrostic_word && (
          <Input label="Acrostic word" placeholder="e.g. HOPE or PAMILYA" maxLength={20} value={s.acrostic_word ?? ''} onChange={e => set({ acrostic_word: e.target.value.replace(/[^A-Za-zÑñ]/g, '') })} />
        )}
        {!controls.lines && form?.rules?.lines && <p className="self-end pb-2 text-xs text-ink-400">Fixed structure: {form.rules.lines} lines{form.rules.syllables ? ` · ${form.rules.syllables.join('-')} syllables` : form.rules.syllables_per_line ? ` · ${form.rules.syllables_per_line} syllables each` : ''}{form.rules.rhyme ? ` · ${form.rules.rhyme}` : ''}</p>}
        <Select label="Vocabulary level" value={s.vocabulary_level} onChange={e => set({ vocabulary_level: e.target.value })}>
          <option value="simple">Simple</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option>
        </Select>
      </div>
      {controls.meter && <Toggle checked={s.traditional_meter} onChange={v => set({ traditional_meter: v })} label="Traditional meter" description="Aim for ~10 syllables per line (iambic pentameter) in English sonnets." />}
      <div>
        <p className="mb-1.5 text-sm font-medium text-ink-300">Emotional tone <span className="font-normal text-ink-400">(optional, up to 3)</span></p>
        <div className="flex flex-wrap gap-1.5">
          {TONES.map(t => {
            const on = s.emotional_tone?.includes(t)
            return <button key={t} type="button" onClick={() => toggleTone(t)} aria-pressed={on}
              className={cx('focus-ring rounded-full border px-2.5 py-1 text-xs capitalize transition-colors', on ? 'border-iris-400 bg-iris-500/20 text-iris-200' : 'border-ink-600 text-ink-300 hover:border-ink-400')}>{t}</button>
          })}
        </div>
      </div>
      <Toggle checked={s.show_vocabulary} onChange={v => set({ show_vocabulary: v })} label="Show vocabulary" description="Explain notable words used in the poem." />
    </div>
  )
}
