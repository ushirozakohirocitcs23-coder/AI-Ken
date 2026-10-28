import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './index.css'
import { AuthProvider, GuestOnly, RequireAuth } from './auth'
import { FullPageSpinner, ToastProvider } from './components/ui'
import Landing from './pages/Landing'
import { ForgotPassword, Login, Register, ResetPassword } from './pages/AuthPages'
import AppLayout from './pages/app/AppLayout'
import Chat from './pages/app/Chat'
import SavedPoems from './pages/app/SavedPoems'
import Profile from './pages/app/Profile'
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'))
const Dashboard = lazy(() => import('./pages/admin/Dashboard'))
const Users = lazy(() => import('./pages/admin/Users'))
const Knowledge = lazy(() => import('./pages/admin/Knowledge'))
const Forms = lazy(() => import('./pages/admin/Forms'))
const Dictionary = lazy(() => import('./pages/admin/Dictionary'))
const Analytics = lazy(() => import('./pages/admin/Analytics'))
const SystemSettings = lazy(() => import('./pages/admin/SystemSettings'))
const AuditLogs = lazy(() => import('./pages/admin/AuditLogs'))
import Privacy from './pages/Privacy'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Suspense fallback={<FullPageSpinner />}>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
            <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/app" element={<RequireAuth role="user"><AppLayout /></RequireAuth>}>
              <Route index element={<Chat />} />
              <Route path="c/:id" element={<Chat />} />
              <Route path="saved" element={<SavedPoems />} />
              <Route path="profile" element={<Profile />} />
            </Route>
            <Route path="/admin" element={<RequireAuth role="admin"><AdminLayout /></RequireAuth>}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<Users />} />
              <Route path="knowledge" element={<Knowledge />} />
              <Route path="forms" element={<Forms />} />
              <Route path="dictionary" element={<Dictionary />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="settings" element={<SystemSettings />} />
              <Route path="audit" element={<AuditLogs />} />
              <Route path="profile" element={<Profile admin />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
)
