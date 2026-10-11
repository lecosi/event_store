import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import type { Event, Page } from '../types'

vi.mock('../api/events')

const event = (id: number, name: string): Event => ({
  id,
  name,
  description: '',
  location: 'Bogotá',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 50,
  status: 'published',
  organizer_id: 1,
})

const pageOf = (items: Event[], overrides: Partial<Page<Event>> = {}): Page<Event> => ({
  items,
  total: items.length,
  page: 1,
  size: 9,
  pages: 1,
  ...overrides,
})

function renderAt(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  render(<RouterProvider router={router} />)
  return router
}

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
})

describe('EventListPage', () => {
  it('lists the events of the first page with the page size', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(
      pageOf([event(1, 'Taller de React'), event(2, 'Charla de Python')]),
    )
    renderAt('/')
    expect(await screen.findByRole('link', { name: 'Taller de React' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Charla de Python' })).toBeInTheDocument()
    expect(eventsApi.listEvents).toHaveBeenCalledWith({ q: undefined, page: 1, size: 9 })
  })

  it('reads the search and the page from the URL', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(
      pageOf([event(3, 'Python')], { page: 2, pages: 3 }),
    )
    renderAt('/?q=python&page=2')
    await screen.findByRole('link', { name: 'Python' })
    expect(eventsApi.listEvents).toHaveBeenCalledWith({ q: 'python', page: 2, size: 9 })
    expect(screen.getByRole('searchbox', { name: 'Buscar eventos' })).toHaveValue('python')
  })

  it('falls back to the first page when the page param is not a positive integer', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(pageOf([]))
    renderAt('/?page=abc')
    await screen.findByText('Aún no hay eventos.')
    expect(eventsApi.listEvents).toHaveBeenCalledWith({ q: undefined, page: 1, size: 9 })
  })

  it('shows a spinner while loading', async () => {
    vi.mocked(eventsApi.listEvents).mockReturnValue(new Promise(() => {}))
    renderAt('/')
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('shows the empty state when there are no events', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(pageOf([]))
    renderAt('/')
    expect(await screen.findByText('Aún no hay eventos.')).toBeInTheDocument()
  })

  it('shows the no results state for a search', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(pageOf([]))
    renderAt('/?q=zzz')
    expect(await screen.findByText('Ningún evento coincide con "zzz".')).toBeInTheDocument()
  })

  it('shows the error message when the request fails', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue(new ApiError('Sin conexión', null))
    renderAt('/')
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin conexión')
  })

  it('puts the debounced search in the URL and resets the page', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(pageOf([event(1, 'Taller')], { pages: 3 }))
    const router = renderAt('/?page=2')
    await screen.findByRole('link', { name: 'Taller' })
    fireEvent.change(screen.getByRole('searchbox', { name: 'Buscar eventos' }), {
      target: { value: 'react' },
    })
    await waitFor(() => expect(router.state.location.search).toBe('?q=react'))
    await waitFor(() =>
      expect(eventsApi.listEvents).toHaveBeenLastCalledWith({ q: 'react', page: 1, size: 9 }),
    )
  })

  it('keeps the search when changing page', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(pageOf([event(1, 'Taller')], { pages: 3 }))
    const router = renderAt('/?q=react')
    await screen.findByRole('link', { name: 'Taller' })
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(router.state.location.search).toBe('?page=2&q=react'))
  })
})
