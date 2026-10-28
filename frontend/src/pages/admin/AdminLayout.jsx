import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { BarChart3, BookA, Database, LayoutDashboard, LogOut, Menu, ScrollText, Settings, ShieldCheck, User, Users, X } from 'lucide-react'
import { useAuth } from '../../auth'
import { Badge, IconButton, Logo, cx } from '../../components/ui'

const NAV = [
  ['/admin', LayoutDashboard, 'Dashboard', true], ['/admin/users', Users, 'Users'], ['/admin/knowledge', Database, 'AI & Knowledge Base'],
  ['/admin/forms', ScrollText, 'Poetry Forms'], ['/admin/dictionary', BookA, 'Dictionary'], ['/admin/analytics', BarChart3, 'Poetry Analytics'],
  ['/admin/settings', Settings, 'System Settings'], ['/admin/audit', ShieldCheck, 'Security & Audit Logs'], ['/admin/profile', User, 'My Profile'],
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [open, setOpen] = useState(false)
  useEffect(() => setOpen(false), [loc.pathname])

  const side = (
    <div className="flex h-full flex-col p-3">
      <div className="flex items-center justify-between px-1 pb-4 pt-1">
        <span className="flex items-center gap-2"><Logo size="sm" /><Badge tone="iris">Admin</Badge></span>
        <IconButton label="Close menu" icon={X} className="lg:hidden" onClick={() => setOpen(false)} />
      </div>
      <nav className="flex-1 space-y-0.5 text-sm">
        {NAV.map(([to, Icon, label, end]) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => cx('focus-ring flex items-center gap-2.5 rounded-lg px-3 py-2', isActive ? 'bg-ink-700 text-ink-100' : 'text-ink-300 hover:bg-ink-800')}>
            <Icon className="h-4 w-4" /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="flex items-center gap-2 border-t border-ink-700 px-1 pt-3">
        <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{user?.full_name}</p><p className="truncate text-xs text-ink-400">{user?.email}</p></div>
        <IconButton label="Log out" icon={LogOut} onClick={async () => { await logout(); nav('/login') }} />
      </div>
    </div>
  )
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden w-64 shrink-0 border-r border-ink-800 bg-ink-950/60 lg:block">{side}</aside>
      {open && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={() => setOpen(false)} />}
      <aside className={cx('fixed inset-y-0 left-0 z-50 w-64 border-r border-ink-800 bg-ink-950 transition-transform lg:hidden', open ? 'translate-x-0' : '-translate-x-full')}>{side}</aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-ink-800 px-3 py-2 lg:hidden"><IconButton label="Open menu" icon={Menu} onClick={() => setOpen(true)} /><Logo size="sm" /></div>
        <div className="scroll-thin flex-1 overflow-y-auto"><div className="mx-auto max-w-7xl px-4 py-8 sm:px-6"><Outlet /></div></div>
      </main>
    </div>
  )
}
