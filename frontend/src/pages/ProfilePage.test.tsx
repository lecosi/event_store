process.env.TZ = 'UTC'

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import * as registrationsApi from '../api/registrations'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import type { EventStatus, Page, RegisteredEvent, Role } from '../types'

vi.mock('../api/events')
vi.mock('../api/registrations')

const registered = (
  id: number,
  name: string,
  status: EventStatus = 'published',
): RegisteredEvent => ({
  id,
  name,
  description: '',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 100,
  status,
  organizer_id: 1,
  registered_at: '2030-01-10T15:30:00Z',
})

const pageOf = (items: RegisteredEvent[], page = 1, pages = 1): Page<RegisteredEvent> => ({
  items,
  total: items.length,
  page,
  size: 10,
  pages,
})

function loginAs(role: Role = 'attendee') {
  useAuthStore.setState({
    token: 'tok',
    user: { id: 7, email: 'ana@example.com', role, is_active: true },
  })
}

function renderPage() {
  const router = createMemoryRouter(routes, { initialEntries: ['/profile'] })
  render(<RouterProvider router={router} />)
  return router
}

const toastMessages = () => useToastStore.getState().toasts.map((t) => t.message)

beforeEach(() => {
  vi.resetAllMocks()
  loginAs()
  useToastStore.setState({ toasts: [] })
  vi.mocked(eventsApi.listEvents).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    size: 9,
    pages: 0,
  })
  vi.mocked(registrationsApi.listMyEvents).mockResolvedValue(
    pageOf([registered(1, 'PyCon Latam'), registered(2, 'Taller de React', 'draft')]),
  )
})

describe('ProfilePage', () => {
  it('sends an anonymous visitor to the login page', async () => {
    useAuthStore.setState({ token: null, user: null })
    const router = renderPage()
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('shows the email and the role label of the user', async () => {
    loginAs('organizer')
    renderPage()
    expect(await screen.findByText('ana@example.com · rol: Organizador')).toBeInTheDocument()
  })

  it('lists the registered events with link, status and date', async () => {
    renderPage()
    const link = await screen.findByRole('link', { name: 'PyCon Latam' })
    expect(link).toHaveAttribute('href', '/events/1')
    const row = link.closest('li') as HTMLElement
    expect(within(row).getByText('Publicado')).toBeInTheDocument()
    expect(within(row).getByText(/2030/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Taller de React' })).toBeInTheDocument()
    expect(registrationsApi.listMyEvents).toHaveBeenCalledWith(1, 10)
  })

  it('shows a spinner while the events load', async () => {
    vi.mocked(registrationsApi.listMyEvents).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('shows the backend message when the events cannot be loaded', async () => {
    vi.mocked(registrationsApi.listMyEvents).mockRejectedValue(new ApiError('Servidor caído.', 500))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Servidor caído.')
  })

  it('shows an empty state that links to the event list', async () => {
    vi.mocked(registrationsApi.listMyEvents).mockResolvedValue(pageOf([], 1, 0))
    renderPage()
    expect(await screen.findByText(/Aún no estás inscrito en ningún evento\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ver eventos' })).toHaveAttribute('href', '/')
  })

  it('loads the requested page with the pagination controls', async () => {
    vi.mocked(registrationsApi.listMyEvents).mockImplementation(async (page) =>
      page === 2
        ? pageOf([registered(11, 'Evento once')], 2, 2)
        : pageOf([registered(1, 'PyCon Latam')], 1, 2),
    )
    renderPage()
    await screen.findByRole('link', { name: 'PyCon Latam' })
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('link', { name: 'Evento once' })).toBeInTheDocument()
    expect(registrationsApi.listMyEvents).toHaveBeenLastCalledWith(2, 10)
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()
  })

  it('ignores the response of a page the user has already left', async () => {
    let resolveFirst: (page: Page<RegisteredEvent>) => void = () => {}
    vi.mocked(registrationsApi.listMyEvents)
      .mockResolvedValueOnce(pageOf([registered(1, 'PyCon Latam')], 1, 3))
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(pageOf([registered(3, 'Evento tres')], 3, 3))
    renderPage()
    await screen.findByRole('link', { name: 'PyCon Latam' })
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(registrationsApi.listMyEvents).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByRole('link', { name: 'Evento tres' })).toBeInTheDocument()
    await act(async () => resolveFirst(pageOf([registered(2, 'Evento dos')], 2, 3)))
    expect(screen.queryByRole('link', { name: 'Evento dos' })).not.toBeInTheDocument()
  })
})

describe('ProfilePage cancelling a registration', () => {
  it('cancels the registration, confirms with a toast and reloads the page', async () => {
    vi.mocked(registrationsApi.unregister).mockResolvedValue()
    renderPage()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Cancelar inscripción en PyCon Latam' }),
    )
    await waitFor(() => expect(toastMessages()).toContain('Inscripción en "PyCon Latam" cancelada'))
    expect(registrationsApi.unregister).toHaveBeenCalledWith(1)
    await waitFor(() => expect(registrationsApi.listMyEvents).toHaveBeenCalledTimes(2))
    expect(registrationsApi.listMyEvents).toHaveBeenLastCalledWith(1, 10)
  })

  it('steps back one page when the last item of a page is cancelled', async () => {
    vi.mocked(registrationsApi.unregister).mockResolvedValue()
    vi.mocked(registrationsApi.listMyEvents).mockImplementation(async (page) =>
      page === 2
        ? pageOf([registered(11, 'Evento once')], 2, 2)
        : pageOf([registered(1, 'PyCon Latam')], 1, 2),
    )
    renderPage()
    await screen.findByRole('link', { name: 'PyCon Latam' })
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    fireEvent.click(
      await screen.findByRole('button', { name: 'Cancelar inscripción en Evento once' }),
    )
    await waitFor(() => expect(registrationsApi.unregister).toHaveBeenCalledWith(11))
    await waitFor(() => expect(registrationsApi.listMyEvents).toHaveBeenLastCalledWith(1, 10))
    expect(await screen.findByRole('link', { name: 'PyCon Latam' })).toBeInTheDocument()
  })

  it('shows the backend message in a toast when cancelling fails', async () => {
    vi.mocked(registrationsApi.unregister).mockRejectedValue(
      new ApiError('No estás inscrito en este evento.', 404),
    )
    renderPage()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Cancelar inscripción en PyCon Latam' }),
    )
    await waitFor(() => expect(toastMessages()).toContain('No estás inscrito en este evento.'))
    expect(registrationsApi.listMyEvents).toHaveBeenCalledTimes(1)
  })

  it('disables cancelling for a finished event and says why', async () => {
    vi.mocked(registrationsApi.listMyEvents).mockResolvedValue(
      pageOf([registered(1, 'PyCon Latam', 'finished'), registered(2, 'Taller de React')]),
    )
    renderPage()
    expect(
      await screen.findByRole('button', { name: 'Cancelar inscripción en PyCon Latam' }),
    ).toBeDisabled()
    expect(
      screen.getByText('No se puede cancelar la inscripción de un evento finalizado.'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Cancelar inscripción en Taller de React' }),
    ).toBeEnabled()
  })
})
