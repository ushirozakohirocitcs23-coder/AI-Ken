import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api'
import { useAuth } from '../../auth'
import { Alert, Badge, Button, Card, ConfirmDialog, Input, PageHeader, fmtDate, useToast } from '../../components/ui'

export default function Profile({ admin }) {
  const { user, setUser, logout } = useAuth()
  const toast = useToast()
  const nav = useNavigate()
  const [name, setName] = useState(user.full_name)
  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [pwErr, setPwErr] = useState('')
  const [saving, setSaving] = useState(null)
  const [confirm, setConfirm] = useState(false)

  const saveName = async (e) => {
    e.preventDefault(); setSaving('name')
    try { setUser((await api('/me/profile', { method: 'PATCH', body: { full_name: name } })).user); toast('Profile updated.') }
    catch (err) { toast(err.message, 'error') } finally { setSaving(null) }
  }
  const savePw = async (e) => {
    e.preventDefault(); setPwErr('')
    if (pw.new_password !== pw.confirm_password) return setPwErr('Passwords do not match.')
    setSaving('pw')
    try { toast((await api('/me/password', { method: 'POST', body: pw })).message); setPw({ current_password: '', new_password: '', confirm_password: '' }) }
    catch (err) { setPwErr(err.message) } finally { setSaving(null) }
  }
  const deleteData = async () => {
    setSaving('del')
    try { toast((await api('/me/data', { method: 'DELETE' })).message); setConfirm(false); nav('/app') }
    catch (err) { toast(err.message, 'error') } finally { setSaving(null) }
  }

  return (
    <div className="scroll-thin flex-1 overflow-y-auto">
      <div className="mx-auto max-w-2xl px-4 py-8 sm:px-6">
        <PageHeader title={admin ? 'Administrator Profile' : 'Profile & Settings'} subtitle={<>{user.email} · <Badge tone={user.role === 'admin' ? 'iris' : 'neutral'}>{user.role}</Badge> · member since {fmtDate(user.created_at).split(',').slice(0, 2).join(',')}</>} />
        <div className="space-y-5">
          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Profile</h2>
            <form onSubmit={saveName} className="space-y-4">
              <Input label="Full name" value={name} onChange={e => setName(e.target.value)} />
              <Input label="Email" value={user.email} disabled hint="Contact an administrator to change your email." />
              <Button type="submit" loading={saving === 'name'} disabled={name.trim().length < 2 || name === user.full_name}>Save changes</Button>
            </form>
          </Card>
          <Card className="p-5">
            <h2 className="mb-4 font-semibold">Change password</h2>
            <form onSubmit={savePw} className="space-y-4">
              {pwErr && <Alert tone="error">{pwErr}</Alert>}
              <Input label="Current password" type="password" autoComplete="current-password" value={pw.current_password} onChange={e => setPw({ ...pw, current_password: e.target.value })} />
              <Input label="New password" type="password" autoComplete="new-password" hint="At least 8 characters with a letter and a number." value={pw.new_password} onChange={e => setPw({ ...pw, new_password: e.target.value })} />
              <Input label="Confirm new password" type="password" autoComplete="new-password" value={pw.confirm_password} onChange={e => setPw({ ...pw, confirm_password: e.target.value })} />
              <Button type="submit" loading={saving === 'pw'} disabled={!pw.current_password || !pw.new_password}>Update password</Button>
            </form>
          </Card>
          {!admin && (
            <Card className="border-rose-500/30 p-5">
              <h2 className="font-semibold">Your data</h2>
              <p className="mt-1 text-sm text-ink-400">Delete every conversation, story and poem you've created. Your account stays active.</p>
              <Button variant="danger" className="mt-4" onClick={() => setConfirm(true)}>Delete my data</Button>
            </Card>
          )}
          <Button variant="secondary" onClick={async () => { await logout(); nav('/login') }}>Log out</Button>
        </div>
      </div>
      <ConfirmDialog open={confirm} onClose={() => setConfirm(false)} onConfirm={deleteData} loading={saving === 'del'} confirmLabel="Delete everything"
        title="Delete all your data?" message="All conversations, stories and poems (including saved poems) will be permanently deleted. This cannot be undone." />
    </div>
  )
}
