process.env.TZ = 'UTC'

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import { useToastStore } from '../store/toastStore'
import type { EventDetail, EventStatus, Role } from '../types'

vi.mock('../api/events')

const detail = (overrides: Partial<EventDetail> = {}): EventDetail => ({
  id: 5,
  name: 'PyCon Latam',
  description: '',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 100,
  status: 'draft',
  organizer_id: 1,
  sessions: [],
  registered_count: 0,
  available_spots: 100,
  is_registered: false,
  ...overrides,
})

function loginAs(role: Role, id = 1) {
  useAuthStore.setState({
    token: 'tok',
    user: { id, email: 'ana@example.com', role, is_active: true },
  })
}

function renderAt(url: string) {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  render(<RouterProvider router={router} />)
  return router
}

function fillCreateForm() {
  fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Taller' } })
  fireEvent.change(screen.getByLabelText('Lugar'), { target: { value: 'Bogotá' } })
  fireEvent.change(screen.getByLabelText('Inicio'), { target: { value: '2999-01-01T10:00' } })
  fireEvent.change(screen.getByLabelText('Fin'), { target: { value: '2999-01-01T12:00' } })
  fireEvent.change(screen.getByLabelText('Capacidad'), { target: { value: '30' } })
}

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
  useToastStore.setState({ toasts: [] })
  useEventStore.setState({ currentEvent: null, detailLoading: false, detailError: null })
})

describe('EventFormPage access', () => {
  it('sends a visitor to the login page', async () => {
    const router = renderAt('/events/new')
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(router.state.location.state).toMatchObject({ from: { pathname: '/events/new' } })
  })

  it('shows a spinner while the profile is still loading', async () => {
    useAuthStore.setState({ token: 'tok', user: null })
    renderAt('/events/new')
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('blocks an attendee from creating events', async () => {
    loginAs('attendee')
    renderAt('/events/new')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No tienes permiso para crear o editar eventos',
    )
    expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument()
  })

  it('blocks an organizer from editing an event of someone else', async () => {
    loginAs('organizer', 2)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail())
    renderAt('/events/5/edit')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No tienes permiso para editar este evento.',
    )
  })
})

describe('EventFormPage create', () => {
  it('shows the creation form for an organizer, not an event detail', async () => {
    loginAs('organizer')
    renderAt('/events/new')
    expect(await screen.findByRole('heading', { name: 'Nuevo evento' })).toBeInTheDocument()
    expect(eventsApi.getEvent).not.toHaveBeenCalled()
  })

  it('creates the event, shows a toast and opens its detail', async () => {
    loginAs('organizer')
    vi.mocked(eventsApi.createEvent).mockResolvedValue(detail({ id: 9, name: 'Taller' }))
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ id: 9, name: 'Taller' }))
    const router = renderAt('/events/new')
    await screen.findByRole('heading', { name: 'Nuevo evento' })
    fillCreateForm()
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/events/9'))
    expect(eventsApi.createEvent).toHaveBeenCalledWith({
      name: 'Taller',
      description: '',
      location: 'Bogotá',
      start_at: '2999-01-01T10:00:00.000Z',
      end_at: '2999-01-01T12:00:00.000Z',
      capacity: 30,
    })
    expect(useToastStore.getState().toasts.map((t) => t.message)).toContain('Evento creado')
  })

  it('shows the backend message inside the form when creating fails', async () => {
    loginAs('admin')
    vi.mocked(eventsApi.createEvent).mockRejectedValue(
      new ApiError('La fecha de inicio debe estar en el futuro.', 422),
    )
    const router = renderAt('/events/new')
    await screen.findByRole('heading', { name: 'Nuevo evento' })
    fillCreateForm()
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La fecha de inicio debe estar en el futuro.',
    )
    expect(router.state.location.pathname).toBe('/events/new')
  })
})

describe('EventFormPage edit', () => {
  it.each<EventStatus>(['cancelled', 'finished'])(
    'shows a message with a link back instead of the form for a %s event',
    async (status) => {
      loginAs('organizer', 1)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt('/events/5/edit')
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Este evento ya no se puede editar porque está cancelado o finalizado.',
      )
      expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Volver al evento' })).toHaveAttribute(
        'href',
        '/events/5',
      )
    },
  )

  it.each<EventStatus>(['draft', 'published'])('shows the form for a %s event', async (status) => {
    loginAs('organizer', 1)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
    renderAt('/events/5/edit')
    expect(await screen.findByLabelText('Nombre')).toBeInTheDocument()
  })

  it('loads the event into the form for its organizer', async () => {
    loginAs('organizer', 1)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail())
    renderAt('/events/5/edit')
    expect(await screen.findByRole('heading', { name: 'Editar evento' })).toBeInTheDocument()
    expect(screen.getByLabelText('Nombre')).toHaveValue('PyCon Latam')
    expect(screen.getByRole('link', { name: 'Volver al evento' })).toHaveAttribute('href', '/events/5')
  })

  it('saves the changes, shows a toast and returns to the detail', async () => {
    loginAs('admin', 99)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail())
    vi.mocked(eventsApi.updateEvent).mockResolvedValue(detail({ name: 'Nuevo nombre' }))
    const router = renderAt('/events/5/edit')
    await screen.findByRole('heading', { name: 'Editar evento' })
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Nuevo nombre' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/events/5'))
    expect(eventsApi.updateEvent).toHaveBeenCalledWith(
      5,
      expect.objectContaining({ name: 'Nuevo nombre', capacity: 100 }),
    )
    expect(useToastStore.getState().toasts.map((t) => t.message)).toContain('Evento actualizado')
  })

  it('shows the backend message when the event cannot be loaded', async () => {
    loginAs('organizer')
    vi.mocked(eventsApi.getEvent).mockRejectedValue(new ApiError('Evento no encontrado.', 404))
    renderAt('/events/5/edit')
    expect(await screen.findByRole('alert')).toHaveTextContent('Evento no encontrado.')
  })

  it('shows an invalid id message without calling the backend', async () => {
    loginAs('organizer')
    renderAt('/events/abc/edit')
    expect(await screen.findByRole('alert')).toHaveTextContent('Identificador de evento no válido')
    expect(eventsApi.getEvent).not.toHaveBeenCalled()
  })

  it('shows a spinner while the event loads', async () => {
    loginAs('organizer')
    vi.mocked(eventsApi.getEvent).mockReturnValue(new Promise(() => {}))
    renderAt('/events/5/edit')
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })
})
