import { useEffect, useRef, useState } from 'react'
import { useNavigate, useOutletContext, useParams } from 'react-router-dom'
import { ArrowUp, SlidersHorizontal, X } from 'lucide-react'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Alert, Badge, Button, IconButton, Logo, Spinner, cx } from '../../components/ui'
import PoemCard, { WritingIndicator } from './PoemCard'
import PoemSettingsPanel, { DEFAULT_SETTINGS, settingsSummary, useForms } from './PoemSettings'

const SUGGESTIONS = [
  'Turn my happiest memory into a poem.',
  'Help me express the sadness I cannot explain.',
  'Write a poem about my dreams and inspiration.',
  'Turn my frustration into powerful words.',
  'Gumawa ng tula tungkol sa aking pamilya.',
  'Isulat ang aking nararamdaman sa isang makabuluhang tula.',
]

const loadSettings = () => {
  try { return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem('aiken.settings') || '{}') } } catch { return DEFAULT_SETTINGS }
}

export default function Chat() {
  const { id } = useParams()
  const convId = id ? Number(id) : null
  const nav = useNavigate()
  const { user } = useAuth()
  const { refreshConversations } = useOutletContext()
  const forms = useForms()
  const [messages, setMessages] = useState([])
  const [loadingConv, setLoadingConv] = useState(false)
  const [notFound, setNotFound] = useState(false)
  const [story, setStory] = useState('')
  const [sending, setSending] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [settings, setSettings] = useState(loadSettings)
  const [showSettings, setShowSettings] = useState(false)
  const [status, setStatus] = useState(null)
  const skipLoad = useRef(null)
  const bottom = useRef(null)
  const input = useRef(null)

  useEffect(() => { api('/meta/status').then(setStatus).catch(() => {}) }, [])
  useEffect(() => { try { localStorage.setItem('aiken.settings', JSON.stringify(settings)) } catch { /* storage unavailable */ } }, [settings])

  useEffect(() => {
    setError(null); setNotFound(false)
    if (!convId) { setMessages([]); return }
    if (skipLoad.current === convId) { skipLoad.current = null; return }
    setLoadingConv(true)
    api(`/conversations/${convId}`).then(r => setMessages(r.messages))
      .catch(e => { if (e.status === 404) setNotFound(true); else setError({ message: e.message }) })
      .finally(() => setLoadingConv(false))
  }, [convId])

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages.length, sending])
  useEffect(() => {
    const el = input.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 220) + 'px'
  }, [story])

  const send = async (text = story) => {
    const t = text.trim()
    if (!t || sending) return
    setError(null); setSending(true); setStory('')
    const temp = { id: `tmp-${Date.now()}`, sender: 'user', content: t }
    setMessages(m => [...m, temp])
    try {
      const r = await api('/generate', { method: 'POST', body: { story: t, conversation_id: convId, settings: { ...settings, acrostic_word: settings.acrostic_word || null } } })
      setMessages(m => [...m.filter(x => x.id !== temp.id), ...r.messages])
      refreshConversations()
      if (!convId) { skipLoad.current = r.conversation.id; nav(`/app/c/${r.conversation.id}`, { replace: true }) }
    } catch (e) {
      setMessages(m => m.filter(x => x.id !== temp.id))
      setStory(t)
      setError(typeof e.detail === 'object' && e.detail ? { message: e.detail.message || e.message, hint: e.detail.setup_hint, code: e.detail.code } : { message: e.message })
    } finally { setSending(false) }
  }

  const onKey = (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send() } }
  const updatePoem = (p) => setMessages(ms => ms.map(m => m.poem?.id === p.id ? { ...m, poem: { ...m.poem, ...p } } : m))
  const addMessage = (m) => { setMessages(ms => [...ms, m]); refreshConversations() }
  const summary = settingsSummary(settings, forms)

  if (notFound) return <div className="p-8"><Alert tone="error">This conversation doesn't exist or was deleted.</Alert></div>

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-6 sm:px-6">
          {status && !status.ai_ready && (
            <Alert tone="warn" title="AI generation isn't configured yet" className="mb-4">
              The administrator needs to add a language-model API key on the server. {status.setup_hint}
            </Alert>
          )}
          {!convId && messages.length === 0 && !sending && (
            <div className="rise pt-6 text-center sm:pt-14">
              <div className="mx-auto mb-5 w-fit"><Logo size="lg" withText={false} /></div>
              <h1 className="font-serif text-2xl font-semibold sm:text-3xl">Kumusta, {user?.full_name?.split(' ')[0]}.</h1>
              <p className="mx-auto mt-3 max-w-xl text-ink-300">Welcome to AI-KEN. Every feeling has a story, and every story deserves to be heard. What would you like to turn into poetry today?</p>
              <div className="mt-8 grid gap-2 text-left sm:grid-cols-2">
                {SUGGESTIONS.map(s => (
                  <button key={s} onClick={() => { setStory(s.endsWith('.') ? s.slice(0, -1) + ': ' : s + ' '); input.current?.focus() }}
                    className="focus-ring rounded-xl border border-ink-700 bg-ink-850/60 px-4 py-3 text-sm text-ink-300 transition-colors hover:border-iris-500/50 hover:text-ink-100">{s}</button>
                ))}
              </div>
              <p className="mt-6 text-xs text-ink-400">Tip: share real details — a place, a person, a moment. Click a suggestion, then add your story.</p>
            </div>
          )}
          {loadingConv && <div className="flex justify-center py-10"><Spinner /></div>}
          <div className="space-y-5">
            {messages.map(m => m.sender === 'user' ? (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-tr-sm bg-ink-700 px-4 py-3 text-[15px]">{m.content}</div>
              </div>
            ) : (
              <div key={m.id} className="space-y-2">
                <p className="flex items-center gap-2 text-sm text-ink-300"><Logo size="sm" withText={false} /> {m.content}</p>
                {m.poem && <PoemCard poem={m.poem} onUpdate={updatePoem} onNewMessage={addMessage} busy={busy || sending} setBusy={setBusy} />}
              </div>
            ))}
            {(sending || busy) && <WritingIndicator />}
          </div>
          <div ref={bottom} className="h-2" />
        </div>
      </div>

      <div className="border-t border-ink-800 bg-ink-900/90 backdrop-blur">
        <div className="mx-auto w-full max-w-3xl px-4 pb-4 pt-3 sm:px-6">
          {error && (
            <Alert tone={error.code === 'llm_not_configured' ? 'warn' : 'error'} className="mb-3" title={error.code === 'llm_not_configured' ? 'Setup needed' : undefined}>
              {error.message}{error.hint && <span className="mt-1 block text-xs opacity-80">{error.hint}</span>}
            </Alert>
          )}
          {showSettings && (
            <div className="rise mb-3 max-h-[55vh] overflow-y-auto rounded-2xl border border-ink-700 bg-ink-850 p-4 scroll-thin">
              <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold">Poem Settings</h2>
                <div className="flex gap-1"><Button size="sm" variant="ghost" onClick={() => setSettings(DEFAULT_SETTINGS)}>Reset</Button><IconButton label="Close settings" icon={X} onClick={() => setShowSettings(false)} /></div></div>
              <PoemSettingsPanel value={settings} onChange={setSettings} compact />
            </div>
          )}
          <div className="rounded-2xl border border-ink-600 bg-ink-850 focus-within:border-iris-500/60">
            <textarea ref={input} rows={1} value={story} onChange={e => setStory(e.target.value)} onKeyDown={onKey} maxLength={status?.max_story_chars || 4000}
              placeholder="Share a story, a memory, or a feeling… (Ibahagi ang iyong kuwento)" aria-label="Your story"
              className="block max-h-56 w-full resize-none bg-transparent px-4 pb-1 pt-3.5 text-[15px] placeholder:text-ink-400 focus:outline-none" />
            <div className="flex items-center gap-2 px-2.5 pb-2.5">
              <button type="button" onClick={() => setShowSettings(s => !s)} aria-expanded={showSettings}
                className={cx('focus-ring flex min-w-0 items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs', showSettings ? 'bg-iris-500/15 text-iris-200' : 'text-ink-300 hover:bg-ink-700')}>
                <SlidersHorizontal className="h-3.5 w-3.5 shrink-0" />
                <span className="hidden truncate sm:inline">{summary.join(' · ')}</span><span className="sm:hidden">Settings</span>
              </button>
              <span className="ml-auto hidden text-[11px] text-ink-400 sm:inline">Enter to send · Shift+Enter for new line</span>
              <Button size="sm" className="h-9 w-9 !px-0" aria-label="Send story" onClick={() => send()} loading={sending} disabled={!story.trim() || busy}>{!sending && <ArrowUp className="h-4 w-4" />}</Button>
            </div>
          </div>
          <p className="mt-2 text-center text-[11px] text-ink-400">AI-KEN interprets emotions from your text — it isn't a diagnosis. Your stories are private to you.</p>
        </div>
      </div>
    </div>
  )
}
