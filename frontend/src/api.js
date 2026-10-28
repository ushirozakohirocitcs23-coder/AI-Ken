// Thin fetch wrapper. Session is an httpOnly cookie; every request sends the CSRF header.
export class ApiError extends Error {
  constructor(status, detail) {
    const msg = typeof detail === 'string' ? detail
      : detail?.message || (Array.isArray(detail) ? detail.map(d => d.msg?.replace(/^Value error, /, '')).join(' ') : 'Request failed')
    super(msg)
    this.status = status
    this.detail = detail
  }
}

export async function api(path, { method = 'GET', body, form, signal } = {}) {
  const headers = { 'X-Requested-With': 'AI-KEN' }
  let payload
  if (form) payload = form
  else if (body !== undefined) { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body) }
  let res
  try {
    res = await fetch(`/api${path}`, { method, headers, body: payload, credentials: 'same-origin', signal })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new ApiError(0, 'Cannot reach the AI-KEN server. Check your connection.')
  }
  let data = null
  const text = await res.text()
  if (text) { try { data = JSON.parse(text) } catch { data = { detail: text } } }
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('aiken:unauthorized'))
    throw new ApiError(res.status, data?.detail ?? 'Request failed')
  }
  return data
}

export const qs = (o) => {
  const p = new URLSearchParams()
  Object.entries(o).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, v) })
  const s = p.toString()
  return s ? `?${s}` : ''
}
