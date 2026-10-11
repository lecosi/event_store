import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

/**
 * Route guard: renders the nested routes for logged-in users, otherwise redirects
 * to /login and remembers the requested location so login can send them back.
 */
export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const location = useLocation()

  if (!token) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}
