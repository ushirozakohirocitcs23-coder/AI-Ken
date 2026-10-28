import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { api } from './api'
import { FullPageSpinner } from './components/ui'

const AuthCtx = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined) // undefined = loading, null = signed out

  const refresh = useCallback(async () => {
    try { setUser((await api('/auth/me')).user) } catch { setUser(null) }
  }, [])

  useEffect(() => { refresh() }, [refresh])
  useEffect(() => {
    const onUnauth = () => setUser(null)
    window.addEventListener('aiken:unauthorized', onUnauth)
    return () => window.removeEventListener('aiken:unauthorized', onUnauth)
  }, [])

  const login = async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', body: { email, password } })
    setUser(r.user)
    return r
  }
  const register = async (body) => {
    const r = await api('/auth/register', { method: 'POST', body })
    setUser(r.user)
    return r
  }
  const logout = async () => {
    try { await api('/auth/logout', { method: 'POST' }) } finally { setUser(null) }
  }
  return <AuthCtx.Provider value={{ user, setUser, refresh, login, register, logout }}>{children}</AuthCtx.Provider>
}

export const useAuth = () => useContext(AuthCtx)

export function RequireAuth({ role, children }) {
  const { user } = useAuth()
  const loc = useLocation()
  if (user === undefined) return <FullPageSpinner />
  if (!user) return <Navigate to="/login" replace state={{ from: loc.pathname }} />
  if (role && user.role !== role) return <Navigate to={user.role === 'admin' ? '/admin' : '/app'} replace />
  return children
}

export function GuestOnly({ children }) {
  const { user } = useAuth()
  if (user === undefined) return <FullPageSpinner />
  if (user) return <Navigate to={user.role === 'admin' ? '/admin' : '/app'} replace />
  return children
}
