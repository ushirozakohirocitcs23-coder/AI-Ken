import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Bookmark, BookOpen, Check, LogOut, Menu, MessageSquare, Pencil, Plus, Search, Trash2, User, X } from 'lucide-react'
import { api, qs } from '../../api'
import { useAuth } from '../../auth'
import { ConfirmDialog, IconButton, Logo, cx, useToast } from '../../components/ui'

function ConvItem({ c, active, onRename, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(c.title)
  if (editing) {
    return (
      <form className="flex items-center gap-1 px-2 py-1" onSubmit={(e) => { e.preventDefault(); onRename(c, title); setEditing(false) }}>
        <input autoFocus value={title} onChange={e => setTitle(e.target.value)} aria-label="Conversation title"
          className="focus-ring w-full rounded-md border border-ink-600 bg-ink-900 px-2 py-1 text-sm" onKeyDown={e => e.key === 'Escape' && setEditing(false)} />
        <IconButton label="Save title" icon={Check} type="submit" />
      </form>
    )
  }
  return (
    <div className={cx('group flex items-center rounded-lg pr-1 text-sm', active ? 'bg-ink-700 text-ink-100' : 'text-ink-300 hover:bg-ink-800')}>
      <Link to={`/app/c/${c.id}`} className="focus-ring min-w-0 flex-1 truncate rounded-lg px-3 py-2" title={c.title}>{c.title}</Link>
      <div className={cx('flex shrink-0', active ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 group-focus-within:opacity-100')}>
        <IconButton label="Rename conversation" icon={Pencil} className="h-7 w-7" onClick={() => setEditing(true)} />
        <IconButton label="Delete conversation" icon={Trash2} className="h-7 w-7 hover:text-rose-300" onClick={() => onDelete(c)} />
      </div>
    </div>
  )
}

function WordOfDay() {
  const [w, setW] = useState(null)
  useEffect(() => { api('/dictionary/word-of-the-day').then(r => setW(r.entry)).catch(() => {}) }, [])
  if (!w) return null
  return (
    <div className="rounded-xl border border-ink-700 bg-ink-800/60 p-3">
      <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-iris-300"><BookOpen className="h-3.5 w-3.5" /> Vocabulary of the Day</p>
      <p className="mt-1.5 font-serif text-lg font-semibold">{w.word} <span className="text-xs font-normal text-ink-400">{w.language === 'fil' ? 'Filipino' : 'English'}</span></p>
      <p className="text-xs text-ink-300">{w.definition}</p>
      {w.example && <p className="mt-1 text-xs italic text-ink-400">“{w.example}”</p>}
    </div>
  )
}

export default function AppLayout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const toast = useToast()
  const [convs, setConvs] = useState([])
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [del, setDel] = useState(null)
  const activeId = Number(loc.pathname.match(/\/app\/c\/(\d+)/)?.[1])

  const refresh = useCallback(() => api(`/conversations${qs({ q })}`).then(r => setConvs(r.conversations)).catch(() => {}), [q])
  useEffect(() => { const t = setTimeout(refresh, 200); return () => clearTimeout(t) }, [refresh])
  useEffect(() => { setOpen(false) }, [loc.pathname])

  const rename = async (c, title) => {
    if (!title.trim() || title === c.title) return
    await api(`/conversations/${c.id}`, { method: 'PATCH', body: { title: title.trim() } })
    refresh()
  }
  const remove = async () => {
    await api(`/conversations/${del.id}${qs({ keep_saved: true })}`, { method: 'DELETE' })
    toast('Conversation deleted. Saved poems were kept.')
    if (del.id === activeId) nav('/app')
    setDel(null); refresh()
  }

  const sidebar = (
    <div className="flex h-full flex-col gap-3 p-3">
      <div className="flex items-center justify-between px-1 pt-1">
        <Link to="/app" className="focus-ring rounded-lg"><Logo size="sm" /></Link>
        <IconButton label="Close menu" icon={X} className="lg:hidden" onClick={() => setOpen(false)} />
      </div>
      <Link to="/app" className="focus-ring flex items-center justify-center gap-2 rounded-xl bg-iris-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-iris-600"><Plus className="h-4 w-4" /> New Poem</Link>
      <nav className="space-y-0.5 text-sm">
        <NavLink to="/app/saved" className={({ isActive }) => cx('focus-ring flex items-center gap-2.5 rounded-lg px-3 py-2', isActive ? 'bg-ink-700' : 'text-ink-300 hover:bg-ink-800')}><Bookmark className="h-4 w-4" /> My Saved Poems</NavLink>
        <NavLink to="/app/profile" className={({ isActive }) => cx('focus-ring flex items-center gap-2.5 rounded-lg px-3 py-2', isActive ? 'bg-ink-700' : 'text-ink-300 hover:bg-ink-800')}><User className="h-4 w-4" /> Profile & Settings</NavLink>
      </nav>
      <div className="mt-1 flex min-h-0 flex-1 flex-col">
        <p className="flex items-center gap-1.5 px-2 pb-2 text-[11px] font-semibold uppercase tracking-wider text-ink-400"><MessageSquare className="h-3.5 w-3.5" /> Conversation History</p>
        <div className="relative mb-2 px-1">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-400" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search" aria-label="Search conversations"
            className="focus-ring w-full rounded-lg border border-ink-700 bg-ink-900 py-1.5 pl-8 pr-2 text-sm placeholder:text-ink-400" />
        </div>
        <div className="scroll-thin min-h-0 flex-1 space-y-0.5 overflow-y-auto">
          {convs.length === 0 && <p className="px-3 py-2 text-xs text-ink-400">{q ? 'No matches.' : 'Your poems will appear here.'}</p>}
          {convs.map(c => <ConvItem key={c.id + c.title} c={c} active={c.id === activeId} onRename={rename} onDelete={setDel} />)}
        </div>
      </div>
      <WordOfDay />
      <div className="flex items-center gap-2 border-t border-ink-700 px-1 pt-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-iris-500 to-sky-500 text-sm font-semibold">{user?.full_name?.[0]?.toUpperCase()}</div>
        <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{user?.full_name}</p><p className="truncate text-xs text-ink-400">{user?.email}</p></div>
        <IconButton label="Log out" icon={LogOut} onClick={async () => { await logout(); nav('/login') }} />
      </div>
    </div>
  )

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-72 shrink-0 border-r border-ink-800 bg-ink-950/60 lg:block">{sidebar}</aside>
      {open && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={cx('fixed inset-y-0 left-0 z-50 w-72 border-r border-ink-800 bg-ink-950 transition-transform lg:hidden', open ? 'translate-x-0' : '-translate-x-full')} aria-hidden={!open}>{sidebar}</aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-ink-800 px-3 py-2 lg:hidden">
          <IconButton label="Open menu" icon={Menu} onClick={() => setOpen(true)} />
          <Logo size="sm" />
        </div>
        <Outlet context={{ refreshConversations: refresh }} />
      </main>
      <ConfirmDialog open={!!del} onClose={() => setDel(null)} onConfirm={remove} title="Delete conversation?"
        message={`“${del?.title}” and its unsaved poems will be permanently deleted. Poems you saved will stay in My Saved Poems.`} />
    </div>
  )
}
