import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '../store/authStore'
import { ProtectedRoute } from './ProtectedRoute'

function LoginProbe() {
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname
  return <p>login, came from {from}</p>
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/profile" element={<p>perfil</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  useAuthStore.setState({ token: null, user: null })
})

describe('ProtectedRoute', () => {
  it('redirects to /login remembering the requested location when logged out', () => {
    renderAt('/profile')
    expect(screen.getByText('login, came from /profile')).toBeInTheDocument()
    expect(screen.queryByText('perfil')).not.toBeInTheDocument()
  })

  it('renders the nested route when logged in', () => {
    useAuthStore.setState({ token: 'tok' })
    renderAt('/profile')
    expect(screen.getByText('perfil')).toBeInTheDocument()
  })
})
