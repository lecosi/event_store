import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import * as registrationsApi from '../api/registrations'
import * as reportsApi from '../api/reports'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import { useToastStore } from '../store/toastStore'
import type { EventDetail, EventStatus, Role, Session } from '../types'

vi.mock('../api/events')
vi.mock('../api/registrations')
vi.mock('../api/reports')

const session = (id: number, title: string, start_at: string): Session => ({
  id,
  event_id: 5,
  title,
  start_at,
  end_at: '2030-05-20T18:00:00Z',
  capacity: 20,
  speaker: { id: 1, name: 'Ada Lovelace' },
  enrolled_count: 0,
  available_spots: 20,
  is_enrolled: false,
})

const detail = (overrides: Partial<EventDetail> = {}): EventDetail => ({
  id: 5,
  name: 'PyCon Latam',
  description: 'Dos días de charlas.',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 100,
  status: 'published',
  organizer_id: 1,
  sessions: [],
  registered_count: 40,
  available_spots: 60,
  is_registered: false,
  ...overrides,
})

function loginAs(role: Role, id = 1) {
  useAuthStore.setState({
    token: 'tok',
    user: { id, email: 'ana@example.com', full_name: 'Ana Pérez', role, is_active: true },
  })
}

function renderAt(url = '/events/5') {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  render(<RouterProvider router={router} />)
  return router
}

const toastMessages = () => useToastStore.getState().toasts.map((t) => t.message)

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
  useToastStore.setState({ toasts: [] })
  useEventStore.setState({ currentEvent: null, detailLoading: false, detailError: null })
  vi.mocked(eventsApi.getEvent).mockResolvedValue(detail())
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('EventDetailPage content', () => {
  it('shows name, status, description, place, dates and available spots', async () => {
    renderAt()
    expect(await screen.findByRole('heading', { name: 'PyCon Latam' })).toBeInTheDocument()
    const info = screen.getByRole('region', { name: 'Información del evento' })
    expect(screen.getAllByText('Publicado').length).toBeGreaterThan(0)
    expect(within(info).getByText('Dos días de charlas.')).toBeInTheDocument()
    expect(within(info).getByText('Medellín')).toBeInTheDocument()
    expect(within(info).getByText('60 de 100 disponibles')).toBeInTheDocument()
    expect(eventsApi.getEvent).toHaveBeenCalledWith(5)
  })

  it('shows a fallback when the event has no description', async () => {
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ description: '' }))
    renderAt()
    expect(await screen.findByText('Sin descripción.')).toBeInTheDocument()
  })

  it('lists the sessions sorted by start time', async () => {
    vi.mocked(eventsApi.getEvent).mockResolvedValue(
      detail({
        sessions: [
          session(2, 'Cierre', '2030-05-20T16:00:00Z'),
          session(1, 'Apertura', '2030-05-20T10:00:00Z'),
        ],
      }),
    )
    renderAt()
    await screen.findByText('Apertura')
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Apertura')
    expect(items[0]).toHaveTextContent('Ada Lovelace')
    expect(items[1]).toHaveTextContent('Cierre')
  })

  it('shows a message when there are no sessions', async () => {
    renderAt()
    expect(await screen.findByText('Aún no hay sesiones programadas.')).toBeInTheDocument()
  })

  it('shows a spinner while the event loads', async () => {
    vi.mocked(eventsApi.getEvent).mockReturnValue(new Promise(() => {}))
    renderAt()
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('shows the backend message when the event cannot be loaded', async () => {
    vi.mocked(eventsApi.getEvent).mockRejectedValue(new ApiError('Evento no encontrado.', 404))
    renderAt()
    expect(await screen.findByRole('alert')).toHaveTextContent('Evento no encontrado.')
  })

  it('shows an invalid id message without calling the backend', async () => {
    renderAt('/events/abc')
    expect(await screen.findByRole('alert')).toHaveTextContent('Identificador de evento no válido')
    expect(eventsApi.getEvent).not.toHaveBeenCalled()
  })
})

describe('EventDetailPage registration', () => {
  it('sends an anonymous visitor to the login page remembering the event', async () => {
    const router = renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Inscribirme' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
    expect(router.state.location.state).toMatchObject({ from: { pathname: '/events/5' } })
    expect(registrationsApi.register).not.toHaveBeenCalled()
  })

  it('registers the user, confirms with a toast and reloads the event', async () => {
    loginAs('attendee', 7)
    vi.mocked(registrationsApi.register).mockResolvedValue({
      user_id: 7,
      event_id: 5,
      created_at: '2030-01-01T00:00:00Z',
    })
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Inscribirme' }))
    await waitFor(() => expect(toastMessages()).toContain('Te has inscrito'))
    expect(registrationsApi.register).toHaveBeenCalledWith(5)
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })

  it('cancels the registration of a registered user', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ is_registered: true }))
    vi.mocked(registrationsApi.unregister).mockResolvedValue()
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Cancelar inscripción' }))
    await waitFor(() => expect(toastMessages()).toContain('Inscripción cancelada'))
    expect(registrationsApi.unregister).toHaveBeenCalledWith(5)
  })

  it('shows the backend message in an error toast when registering fails', async () => {
    loginAs('attendee', 7)
    vi.mocked(registrationsApi.register).mockRejectedValue(
      new ApiError('El evento está lleno.', 409),
    )
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Inscribirme' }))
    await waitFor(() => expect(toastMessages()).toContain('El evento está lleno.'))
  })

  it.each<EventStatus>(['draft', 'cancelled', 'finished'])(
    'disables registration with a reason when the event is %s',
    async (status) => {
      loginAs('attendee', 7)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt()
      expect(await screen.findByRole('button', { name: 'Inscribirme' })).toBeDisabled()
      expect(screen.getByText('Las inscripciones están cerradas.')).toBeInTheDocument()
    },
  )

  it('disables registration with a reason when the event is full', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ available_spots: 0 }))
    renderAt()
    expect(await screen.findByRole('button', { name: 'Inscribirme' })).toBeDisabled()
    expect(screen.getByText('Este evento está lleno.')).toBeInTheDocument()
  })

  it('keeps cancelling enabled for a registered user when the event is full', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(
      detail({ available_spots: 0, is_registered: true }),
    )
    renderAt()
    expect(await screen.findByRole('button', { name: 'Cancelar inscripción' })).toBeEnabled()
  })
})

describe('EventDetailPage registration by status', () => {
  it('disables cancelling for a registered user of a finished event and says why', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(
      detail({ status: 'finished', is_registered: true }),
    )
    renderAt()
    expect(await screen.findByRole('button', { name: 'Cancelar inscripción' })).toBeDisabled()
    expect(
      screen.getByText('No se puede cancelar la inscripción de un evento finalizado.'),
    ).toBeInTheDocument()
  })

  it.each<EventStatus>(['draft', 'published', 'cancelled'])(
    'keeps cancelling enabled for a registered user of a %s event',
    async (status) => {
      loginAs('attendee', 7)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status, is_registered: true }))
      renderAt()
      expect(await screen.findByRole('button', { name: 'Cancelar inscripción' })).toBeEnabled()
    },
  )
})

describe('EventDetailPage edit link by status', () => {
  it.each<EventStatus>(['draft', 'published'])(
    'shows the edit link for a %s event',
    async (status) => {
      loginAs('organizer', 1)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt()
      const panel = await screen.findByRole('region', { name: 'Administrar evento' })
      expect(within(panel).getByRole('link', { name: 'Editar evento' })).toBeInTheDocument()
    },
  )

  it.each<EventStatus>(['cancelled', 'finished'])(
    'hides the edit link for a %s event',
    async (status) => {
      loginAs('organizer', 1)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt()
      const panel = await screen.findByRole('region', { name: 'Administrar evento' })
      expect(within(panel).queryByRole('link', { name: 'Editar evento' })).not.toBeInTheDocument()
      expect(within(panel).getByRole('button', { name: 'Eliminar evento' })).toBeInTheDocument()
    },
  )
})

describe('EventDetailPage management', () => {
  it.each<[string, Role, number]>([
    ['the owner organizer', 'organizer', 1],
    ['an admin', 'admin', 99],
  ])('shows the manager panel to %s', async (_label, role, id) => {
    loginAs(role, id)
    renderAt()
    const panel = await screen.findByRole('region', { name: 'Administrar evento' })
    expect(within(panel).getByRole('link', { name: 'Editar evento' })).toHaveAttribute(
      'href',
      '/events/5/edit',
    )
  })

  it.each<[string, Role, number | null]>([
    ['an attendee', 'attendee', 1],
    ['another organizer', 'organizer', 2],
    ['a visitor', 'attendee', null],
  ])('hides the manager panel from %s', async (_label, role, id) => {
    if (id !== null) loginAs(role, id)
    renderAt()
    await screen.findByRole('heading', { name: 'PyCon Latam' })
    expect(screen.queryByRole('region', { name: 'Administrar evento' })).not.toBeInTheDocument()
  })

  it('downloads the participants of this event and confirms with a toast', async () => {
    loginAs('organizer', 1)
    vi.mocked(reportsApi.downloadParticipantsCsv).mockResolvedValue()
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Descargar participantes' }))
    await waitFor(() => expect(toastMessages()).toContain('Reporte descargado'))
    expect(reportsApi.downloadParticipantsCsv).toHaveBeenCalledWith({ event_id: 5 })
  })

  it('disables the participants download while it is running', async () => {
    loginAs('organizer', 1)
    vi.mocked(reportsApi.downloadParticipantsCsv).mockReturnValue(new Promise(() => {}))
    renderAt()
    const button = await screen.findByRole('button', { name: 'Descargar participantes' })
    fireEvent.click(button)
    await waitFor(() => expect(button).toBeDisabled())
  })

  it('shows the backend message in a toast when the participants download fails', async () => {
    loginAs('organizer', 1)
    vi.mocked(reportsApi.downloadParticipantsCsv).mockRejectedValue(
      new ApiError('No tienes permisos para realizar esta acción.', 403),
    )
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Descargar participantes' }))
    await waitFor(() =>
      expect(toastMessages()).toContain('No tienes permisos para realizar esta acción.'),
    )
  })

  it('offers only the allowed next statuses', async () => {
    loginAs('organizer', 1)
    renderAt()
    const select = await screen.findByLabelText('Cambiar estado')
    const options = within(select)
      .getAllByRole('option')
      .map((o) => o.textContent)
    expect(options).toEqual(['Selecciona un estado', 'Finalizado', 'Cancelado'])
  })

  it('offers no status change for a finished event', async () => {
    loginAs('organizer', 1)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status: 'finished' }))
    renderAt()
    await screen.findByRole('region', { name: 'Administrar evento' })
    expect(screen.queryByLabelText('Cambiar estado')).not.toBeInTheDocument()
  })

  it('applies the chosen status, confirms with a toast and reloads', async () => {
    loginAs('organizer', 1)
    vi.mocked(eventsApi.updateStatus).mockResolvedValue(detail({ status: 'cancelled' }))
    renderAt()
    const apply = await screen.findByRole('button', { name: 'Aplicar estado' })
    expect(apply).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Cambiar estado'), { target: { value: 'cancelled' } })
    fireEvent.click(apply)
    await waitFor(() => expect(toastMessages()).toContain('Estado cambiado a Cancelado'))
    expect(eventsApi.updateStatus).toHaveBeenCalledWith(5, 'cancelled')
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })

  it('shows the backend message when the status change is rejected', async () => {
    loginAs('organizer', 1)
    vi.mocked(eventsApi.updateStatus).mockRejectedValue(new ApiError('No se puede cambiar.', 409))
    renderAt()
    await screen.findByLabelText('Cambiar estado')
    fireEvent.change(screen.getByLabelText('Cambiar estado'), { target: { value: 'finished' } })
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar estado' }))
    await waitFor(() => expect(toastMessages()).toContain('No se puede cambiar.'))
  })

  it('deletes the event after confirming and goes back to the list', async () => {
    loginAs('organizer', 1)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(eventsApi.deleteEvent).mockResolvedValue()
    vi.mocked(eventsApi.listEvents).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      size: 9,
      pages: 0,
    })
    const router = renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar evento' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
    expect(eventsApi.deleteEvent).toHaveBeenCalledWith(5)
    expect(toastMessages()).toContain('Evento eliminado')
  })

  it('does not delete when the confirmation is declined', async () => {
    loginAs('organizer', 1)
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar evento' }))
    expect(eventsApi.deleteEvent).not.toHaveBeenCalled()
  })

  it('stays on the page and shows the message when deleting fails', async () => {
    loginAs('organizer', 1)
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(eventsApi.deleteEvent).mockRejectedValue(new ApiError('Sin permisos.', 403))
    const router = renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar evento' }))
    await waitFor(() => expect(toastMessages()).toContain('Sin permisos.'))
    expect(router.state.location.pathname).toBe('/events/5')
    expect(screen.getByRole('button', { name: 'Eliminar evento' })).toBeEnabled()
  })
})

describe('EventDetailPage session enrollment', () => {
  const registeredEvent = (sessionOverrides: Partial<Session> = {}) =>
    detail({
      is_registered: true,
      sessions: [{ ...session(1, 'Apertura', '2030-05-20T10:00:00Z'), ...sessionOverrides }],
    })

  it('does not offer session enrollment to an anonymous visitor', async () => {
    vi.mocked(eventsApi.getEvent).mockResolvedValue(registeredEvent())
    renderAt()
    await screen.findByText('Apertura')
    expect(screen.queryByRole('button', { name: /sesión Apertura/ })).not.toBeInTheDocument()
  })

  it('enrolls the user in the session, confirms with a toast and reloads the event', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(registeredEvent())
    vi.mocked(registrationsApi.enrollInSession).mockResolvedValue({
      user_id: 7,
      session_id: 1,
      created_at: '2030-01-01T00:00:00Z',
    })
    renderAt()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
    )
    await waitFor(() => expect(toastMessages()).toContain('Inscripción a la sesión realizada'))
    expect(registrationsApi.enrollInSession).toHaveBeenCalledWith(5, 1)
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })

  it('cancels the enrollment of an enrolled user', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(registeredEvent({ is_enrolled: true }))
    vi.mocked(registrationsApi.cancelSessionEnrollment).mockResolvedValue()
    renderAt()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Cancelar inscripción en la sesión Apertura' }),
    )
    await waitFor(() => expect(toastMessages()).toContain('Inscripción a la sesión cancelada'))
    expect(registrationsApi.cancelSessionEnrollment).toHaveBeenCalledWith(5, 1)
  })

  it('shows the backend message in an error toast when enrolling fails', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue(registeredEvent())
    vi.mocked(registrationsApi.enrollInSession).mockRejectedValue(
      new ApiError('La sesión está llena.', 409),
    )
    renderAt()
    fireEvent.click(
      await screen.findByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
    )
    await waitFor(() => expect(toastMessages()).toContain('La sesión está llena.'))
    expect(screen.getByRole('button', { name: 'Inscribirme en la sesión Apertura' })).toBeEnabled()
  })

  it('asks a user who is not registered to the event to register first', async () => {
    loginAs('attendee', 7)
    vi.mocked(eventsApi.getEvent).mockResolvedValue({ ...registeredEvent(), is_registered: false })
    renderAt()
    expect(
      await screen.findByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
    ).toBeDisabled()
    expect(
      screen.getByText('Inscríbete al evento para poder inscribirte en sus sesiones.'),
    ).toBeInTheDocument()
  })
})

describe('EventDetailPage when the session ends', () => {
  it('reloads the event and stops showing it when it is no longer visible', async () => {
    loginAs('organizer', 1)
    renderAt()
    await screen.findByRole('heading', { name: 'PyCon Latam' })
    vi.mocked(eventsApi.getEvent).mockRejectedValue(new ApiError('Evento no encontrado.', 404))

    act(() => useAuthStore.getState().logout())

    expect(await screen.findByRole('alert')).toHaveTextContent('Evento no encontrado.')
    expect(screen.queryByRole('heading', { name: 'PyCon Latam' })).not.toBeInTheDocument()
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })
})
