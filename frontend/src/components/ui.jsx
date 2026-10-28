import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'
import { AlertTriangle, CheckCircle2, Eye, EyeOff, Info, Loader2, X } from 'lucide-react'

export const cx = (...c) => c.filter(Boolean).join(' ')

export function Logo({ size = 'md', withText = true }) {
  const s = size === 'lg' ? 'h-10 w-10' : size === 'sm' ? 'h-7 w-7' : 'h-8 w-8'
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg viewBox="0 0 64 64" className={s} aria-hidden="true">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#a594f9" /><stop offset="1" stopColor="#6ea8fe" /></linearGradient></defs>
        <rect width="64" height="64" rx="16" fill="#131b31" />
        <path d="M20 46c10-2 18-10 22-26-8 6-16 10-24 12 2 5 2 9 2 14z" fill="url(#lg)" />
        <path d="M18 48c4-8 10-14 18-20" stroke="#e9e5ff" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </svg>
      {withText && <span className={cx('font-serif font-semibold tracking-tight', size === 'lg' ? 'text-2xl' : 'text-lg')}>AI-KEN</span>}
    </span>
  )
}

const variants = {
  primary: 'bg-iris-500 hover:bg-iris-600 text-white shadow-[0_0_0_1px_rgb(255_255_255/0.06)_inset]',
  secondary: 'bg-ink-800 hover:bg-ink-700 text-ink-100 border border-ink-600',
  ghost: 'hover:bg-ink-800 text-ink-300 hover:text-ink-100',
  danger: 'bg-rose-600/90 hover:bg-rose-600 text-white',
  subtle: 'bg-iris-500/10 hover:bg-iris-500/20 text-iris-300 border border-iris-500/20',
}

export function Button({ variant = 'primary', size = 'md', loading, className, children, icon: Icon, ...props }) {
  const sz = size === 'sm' ? 'h-8 px-3 text-sm gap-1.5' : size === 'lg' ? 'h-12 px-6 text-base gap-2' : 'h-10 px-4 text-sm gap-2'
  return (
    <button {...props} disabled={props.disabled || loading}
      className={cx('focus-ring inline-flex items-center justify-center rounded-xl font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed', sz, variants[variant], className)}>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
      {children}
    </button>
  )
}

export function IconButton({ label, icon: Icon, className, active, ...props }) {
  return (
    <button {...props} aria-label={label} title={label}
      className={cx('focus-ring inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-300 hover:bg-ink-700 hover:text-ink-100 disabled:opacity-40', active && 'text-iris-300 bg-iris-500/10', className)}>
      <Icon className="h-4 w-4" aria-hidden="true" />
    </button>
  )
}

export function Field({ label, error, hint, children, id }) {
  return (
    <div className="space-y-1.5">
      {label && <label htmlFor={id} className="block text-sm font-medium text-ink-300">{label}</label>}
      {children}
      {error ? <p className="text-xs text-rose-400" role="alert">{error}</p> : hint ? <p className="text-xs text-ink-400">{hint}</p> : null}
    </div>
  )
}

const inputCls = 'focus-ring w-full rounded-xl border border-ink-600 bg-ink-850 px-3.5 py-2.5 text-sm text-ink-100 placeholder:text-ink-400 transition-colors hover:border-ink-400/60'

export function Input({ label, error, hint, className, type = 'text', ...props }) {
  const id = useId()
  const [show, setShow] = useState(false)
  const isPw = type === 'password'
  return (
    <Field label={label} error={error} hint={hint} id={id}>
      <div className="relative">
        <input id={id} type={isPw && show ? 'text' : type} aria-invalid={!!error} {...props}
          className={cx(inputCls, isPw && 'pr-10', error && 'border-rose-500/70', className)} />
        {isPw && (
          <button type="button" onClick={() => setShow(s => !s)} aria-label={show ? 'Hide password' : 'Show password'}
            className="focus-ring absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-ink-400 hover:text-ink-100">
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        )}
      </div>
    </Field>
  )
}

export function Textarea({ label, error, hint, className, ...props }) {
  const id = useId()
  return <Field label={label} error={error} hint={hint} id={id}><textarea id={id} {...props} className={cx(inputCls, 'min-h-28 resize-y', className)} /></Field>
}

export function Select({ label, hint, className, children, ...props }) {
  const id = useId()
  return (
    <Field label={label} hint={hint} id={id}>
      <select id={id} {...props} className={cx(inputCls, 'appearance-none bg-[url("data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 20 20%27 fill=%27%237d89a8%27%3E%3Cpath d=%27M5.5 7.5l4.5 4.5 4.5-4.5%27 stroke=%27%237d89a8%27 stroke-width=%271.5%27 fill=%27none%27/%3E%3C/svg%3E")] bg-[length:18px] bg-[right_10px_center] bg-no-repeat pr-9', className)}>
        {children}
      </select>
    </Field>
  )
}

export function Toggle({ checked, onChange, label, description }) {
  return (
    <label className="flex cursor-pointer items-start justify-between gap-3">
      <span>
        <span className="block text-sm font-medium text-ink-100">{label}</span>
        {description && <span className="block text-xs text-ink-400">{description}</span>}
      </span>
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
        className={cx('focus-ring relative mt-0.5 h-5 w-9 shrink-0 rounded-full transition-colors', checked ? 'bg-iris-500' : 'bg-ink-600')}>
        <span className={cx('absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform', checked ? 'translate-x-4' : 'translate-x-0.5')} />
      </button>
    </label>
  )
}

export function Card({ className, children, ...p }) {
  return <div {...p} className={cx('rounded-2xl border border-ink-700 bg-ink-850/80', className)}>{children}</div>
}

const badgeTones = {
  neutral: 'bg-ink-700 text-ink-300', iris: 'bg-iris-500/15 text-iris-300', green: 'bg-emerald-500/15 text-emerald-300',
  amber: 'bg-amber-500/15 text-amber-300', red: 'bg-rose-500/15 text-rose-300', blue: 'bg-sky-500/15 text-sky-300',
}
export function Badge({ tone = 'neutral', children, className }) {
  return <span className={cx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium', badgeTones[tone], className)}>{children}</span>
}

export function Spinner({ className }) { return <Loader2 className={cx('h-5 w-5 animate-spin text-iris-400', className)} aria-label="Loading" /> }
export function FullPageSpinner() { return <div className="flex h-full min-h-screen items-center justify-center"><Spinner className="h-8 w-8" /></div> }

export function Alert({ tone = 'info', title, children, className }) {
  const map = { info: ['border-sky-500/30 bg-sky-500/10 text-sky-200', Info], warn: ['border-amber-500/30 bg-amber-500/10 text-amber-100', AlertTriangle],
    error: ['border-rose-500/30 bg-rose-500/10 text-rose-100', AlertTriangle], success: ['border-emerald-500/30 bg-emerald-500/10 text-emerald-100', CheckCircle2] }
  const [cls, Icon] = map[tone]
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={cx('flex gap-3 rounded-xl border px-4 py-3 text-sm', cls, className)}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0">{title && <p className="font-medium">{title}</p>}<div className="opacity-90">{children}</div></div>
    </div>
  )
}

export function Modal({ open, onClose, title, children, footer, wide }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    document.addEventListener('keydown', onKey)
    ref.current?.querySelector('input,textarea,select,button')?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-0 backdrop-blur-sm sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose?.()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={cx('rise max-h-[92vh] w-full overflow-y-auto rounded-t-2xl border border-ink-700 bg-ink-850 shadow-2xl scroll-thin sm:rounded-2xl', wide ? 'sm:max-w-3xl' : 'sm:max-w-lg')}>
        <div className="flex items-center justify-between border-b border-ink-700 px-5 py-4">
          <h2 className="font-semibold">{title}</h2>
          <IconButton label="Close" icon={X} onClick={onClose} />
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-ink-700 px-5 py-3">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmDialog({ open, title, message, confirmLabel = 'Delete', onConfirm, onClose, loading, tone = 'danger' }) {
  return (
    <Modal open={open} onClose={onClose} title={title}
      footer={<><Button variant="secondary" onClick={onClose}>Cancel</Button><Button variant={tone} loading={loading} onClick={onConfirm}>{confirmLabel}</Button></>}>
      <p className="text-sm text-ink-300">{message}</p>
    </Modal>
  )
}

const ToastCtx = createContext(() => {})
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, tone = 'success') => {
    const id = Math.random()
    setToasts(t => [...t, { id, message, tone }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }, [])
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 left-1/2 z-[60] flex w-full max-w-sm -translate-x-1/2 flex-col gap-2 px-4" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={cx('rise pointer-events-auto rounded-xl border px-4 py-2.5 text-sm shadow-xl backdrop-blur',
            t.tone === 'error' ? 'border-rose-500/40 bg-rose-950/90 text-rose-100' : 'border-ink-600 bg-ink-800/95 text-ink-100')}>{t.message}</div>
        ))}
      </div>
    </ToastCtx.Provider>
  )
}
export const useToast = () => useContext(ToastCtx)

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-ink-600 px-6 py-14 text-center">
      {Icon && <Icon className="mb-3 h-8 w-8 text-ink-400" aria-hidden="true" />}
      <p className="font-medium">{title}</p>
      {children && <p className="mt-1 max-w-sm text-sm text-ink-400">{children}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="font-serif text-2xl font-semibold tracking-tight">{title}</h1>{subtitle && <p className="mt-1 text-sm text-ink-400">{subtitle}</p>}</div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export const LANG = { fil: 'Filipino', en: 'English', taglish: 'Taglish', auto: 'Auto-detect', any: 'Any' }
export const fmtDate = (s) => s ? new Date(s).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }) : '—'
