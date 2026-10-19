import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function ProtectedRoute() {
  const { user, isInitializing } = useAuth()
  const location = useLocation()

  if (isInitializing) {
    return <p className="status-message">Loading session…</p>
  }

  return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />
}
