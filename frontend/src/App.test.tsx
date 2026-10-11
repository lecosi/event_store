import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from './api/auth'
import App from './App'
import { useAuthStore } from './store/authStore'

vi.mock('./api/auth')

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
})

describe('App', () => {
  it('restores the user from the persisted token once on startup', async () => {
    useAuthStore.setState({ token: 'saved' })
    vi.mocked(authApi.fetchMe).mockResolvedValue({
      id: 1,
      email: 'ana@example.com',
      role: 'attendee',
      is_active: true,
    })
    render(<App />)
    expect(await screen.findByText('ana@example.com')).toBeInTheDocument()
    expect(authApi.fetchMe).toHaveBeenCalledTimes(1)
  })

  it('does not call the backend on startup when logged out', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
    expect(authApi.fetchMe).not.toHaveBeenCalled()
  })
})
