import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth'
import { Alert, Button, Input, Logo } from '../components/ui'

function Shell({ title, subtitle, children, footer }) {
  return (
    <div className="glow flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <Link to="/" className="mb-8" aria-label="AI-KEN home"><Logo size="lg" /></Link>
      <div className="rise w-full max-w-md rounded-3xl border border-ink-700 bg-ink-850/90 p-6 shadow-2xl sm:p-8">
        <h1 className="font-serif text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
      {footer && <p className="mt-6 text-sm text-ink-400">{footer}</p>}
    </div>
  )
}

const emailOk = (e) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)
const pwOk = (p) => p.length >= 8 && /[A-Za-z]/.test(p) && /\d/.test(p)

export function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [f, setF] = useState({ email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!emailOk(f.email)) errs.email = 'Enter a valid email address.'
    if (!f.password) errs.password = 'Enter your password.'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setLoading(true); setError('')
    try {
      const r = await login(f.email.trim(), f.password)
      const from = loc.state?.from
      nav(from && from.startsWith(r.redirect) ? from : r.redirect, { replace: true })
    } catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return (
    <Shell title="Welcome back" subtitle="Log in to continue turning stories into poems." footer={<>New to AI-KEN? <Link className="text-iris-300 hover:underline" to="/register">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert tone="error">{error}</Alert>}
        <Input label="Email" type="email" autoComplete="email" value={f.email} error={errors.email} onChange={e => setF({ ...f, email: e.target.value })} />
        <Input label="Password" type="password" autoComplete="current-password" value={f.password} error={errors.password} onChange={e => setF({ ...f, password: e.target.value })} />
        <div className="flex justify-end"><Link to="/forgot-password" className="text-sm text-iris-300 hover:underline">Forgot password?</Link></div>
        <Button type="submit" className="w-full" loading={loading}>Log in</Button>
      </form>
    </Shell>
  )
}

export function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({ full_name: '', email: '', password: '', confirm_password: '' })
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    const errs = {}
    if (f.full_name.trim().length < 2) errs.full_name = 'Please enter your full name.'
    if (!emailOk(f.email)) errs.email = 'Enter a valid email address.'
    if (!pwOk(f.password)) errs.password = 'At least 8 characters with a letter and a number.'
    if (f.password !== f.confirm_password) errs.confirm_password = 'Passwords do not match.'
    setErrors(errs)
    if (Object.keys(errs).length) return
    setLoading(true); setError('')
    try { await register({ ...f, email: f.email.trim() }); nav('/app', { replace: true }) }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return (
    <Shell title="Create your account" subtitle="Your stories stay private to you." footer={<>Already have an account? <Link className="text-iris-300 hover:underline" to="/login">Log in</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && <Alert tone="error">{error}</Alert>}
        <Input label="Full name" autoComplete="name" value={f.full_name} error={errors.full_name} onChange={set('full_name')} />
        <Input label="Email" type="email" autoComplete="email" value={f.email} error={errors.email} onChange={set('email')} />
        <Input label="Password" type="password" autoComplete="new-password" value={f.password} error={errors.password} hint="At least 8 characters with a letter and a number." onChange={set('password')} />
        <Input label="Confirm password" type="password" autoComplete="new-password" value={f.confirm_password} error={errors.confirm_password} onChange={set('confirm_password')} />
        <Button type="submit" className="w-full" loading={loading}>Create account</Button>
        <p className="text-center text-xs text-ink-400">By signing up you agree to our <Link to="/privacy" className="underline">privacy policy</Link>.</p>
      </form>
    </Shell>
  )
}

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    if (!emailOk(email)) return setError('Enter a valid email address.')
    setLoading(true); setError('')
    try { setResult(await api('/auth/forgot-password', { method: 'POST', body: { email: email.trim() } })) }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return (
    <Shell title="Reset your password" subtitle="We'll email you a link to choose a new password." footer={<Link className="text-iris-300 hover:underline" to="/login">Back to log in</Link>}>
      {result ? (
        <div className="space-y-3">
          <Alert tone="success">{result.message}</Alert>
          {result.dev_reset_link && (
            <Alert tone="warn" title="Development mode">
              {result.dev_note} <a className="break-all underline" href={result.dev_reset_link}>Open reset link</a>
            </Alert>
          )}
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate>
          {error && <Alert tone="error">{error}</Alert>}
          <Input label="Email" type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} />
          <Button type="submit" className="w-full" loading={loading}>Send reset link</Button>
        </form>
      )}
    </Shell>
  )
}

export function ResetPassword() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const token = params.get('token') || ''
  const [f, setF] = useState({ password: '', confirm_password: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (e) => {
    e.preventDefault()
    if (!pwOk(f.password)) return setError('Password must be at least 8 characters with a letter and a number.')
    if (f.password !== f.confirm_password) return setError('Passwords do not match.')
    setLoading(true); setError('')
    try { setDone((await api('/auth/reset-password', { method: 'POST', body: { token, ...f } })).message); setTimeout(() => nav('/login'), 1800) }
    catch (err) { setError(err.message) } finally { setLoading(false) }
  }
  return (
    <Shell title="Choose a new password">
      {!token ? <Alert tone="error">This reset link is missing its token. Please request a new link.</Alert>
        : done ? <Alert tone="success">{done}</Alert> : (
          <form onSubmit={submit} className="space-y-4" noValidate>
            {error && <Alert tone="error">{error}</Alert>}
            <Input label="New password" type="password" autoComplete="new-password" value={f.password} onChange={e => setF({ ...f, password: e.target.value })} />
            <Input label="Confirm new password" type="password" autoComplete="new-password" value={f.confirm_password} onChange={e => setF({ ...f, confirm_password: e.target.value })} />
            <Button type="submit" className="w-full" loading={loading}>Reset password</Button>
          </form>
        )}
    </Shell>
  )
}
