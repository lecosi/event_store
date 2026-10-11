import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from './api/auth'
import * as eventsApi from './api/events'
import App from './App'
import { useAuthStore } from './store/authStore'

vi.mock('./api/auth')
vi.mock('./api/events')

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
  vi.mocked(eventsApi.listEvents).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    size: 9,
    pages: 0,
  })
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
    expect(await screen.findByRole('heading', { name: 'Eventos' })).toBeInTheDocument()
    expect(authApi.fetchMe).not.toHaveBeenCalled()
  })
})
