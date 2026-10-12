process.env.TZ = 'UTC'

import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import * as sessionsApi from '../api/sessions'
import * as speakersApi from '../api/speakers'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import { useToastStore } from '../store/toastStore'
import type { EventDetail, EventStatus, Role, Session } from '../types'

vi.mock('../api/events')
vi.mock('../api/sessions')
vi.mock('../api/speakers')

const opening: Session = {
  id: 1,
  event_id: 5,
  title: 'Apertura',
  start_at: '2030-05-20T10:00:00Z',
  end_at: '2030-05-20T11:00:00Z',
  capacity: 20,
  speaker: { id: 3, name: 'Ada Lovelace' },
  enrolled_count: 0,
  available_spots: 20,
  is_enrolled: false,
}

const detail = (overrides: Partial<EventDetail> = {}): EventDetail => ({
  id: 5,
  name: 'PyCon Latam',
  description: '',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 100,
  status: 'published',
  organizer_id: 1,
  sessions: [opening],
  registered_count: 0,
  available_spots: 100,
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

function fill(values: Record<string, string>) {
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
}

async function pickSpeaker(name: string) {
  fireEvent.focus(screen.getByLabelText('Ponente'))
  fireEvent.click(await screen.findByRole('button', { name }))
}

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
  useToastStore.setState({ toasts: [] })
  useEventStore.setState({ currentEvent: null, detailLoading: false, detailError: null })
  vi.mocked(eventsApi.getEvent).mockResolvedValue(detail())
  vi.mocked(speakersApi.listSpeakers).mockResolvedValue({
    items: [{ id: 4, name: 'Grace Hopper', bio: '', email: null }],
    total: 1,
    page: 1,
    size: 10,
    pages: 1,
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('EventDetailPage session actions visibility', () => {
  it.each<[string, Role, number]>([
    ['the owner organizer', 'organizer', 1],
    ['an admin', 'admin', 99],
  ])('shows add, edit and delete to %s', async (_label, role, id) => {
    loginAs(role, id)
    renderAt()
    expect(await screen.findByRole('button', { name: 'Agregar sesión' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Editar sesión Apertura' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Eliminar sesión Apertura' })).toBeInTheDocument()
  })

  it.each<[string, Role, number | null]>([
    ['an attendee', 'attendee', 1],
    ['another organizer', 'organizer', 2],
    ['a visitor', 'attendee', null],
  ])('hides the session actions from %s', async (_label, role, id) => {
    if (id !== null) loginAs(role, id)
    renderAt()
    await screen.findByText('Apertura')
    expect(screen.queryByRole('button', { name: 'Agregar sesión' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Editar sesión Apertura' })).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Eliminar sesión Apertura' }),
    ).not.toBeInTheDocument()
  })

  it.each<EventStatus>(['cancelled', 'finished'])(
    'hides the session actions and says why when the event is %s',
    async (status) => {
      loginAs('organizer', 1)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt()
      await screen.findByText('Apertura')
      expect(
        screen.getByText(
          'Este evento está cancelado o finalizado: ya no se pueden cambiar sus sesiones.',
        ),
      ).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Agregar sesión' })).not.toBeInTheDocument()
      expect(
        screen.queryByRole('button', { name: 'Editar sesión Apertura' }),
      ).not.toBeInTheDocument()
      expect(
        screen.queryByRole('button', { name: 'Eliminar sesión Apertura' }),
      ).not.toBeInTheDocument()
    },
  )

  it.each<EventStatus>(['draft', 'published'])(
    'shows the session actions when the event is %s',
    async (status) => {
      loginAs('organizer', 1)
      vi.mocked(eventsApi.getEvent).mockResolvedValue(detail({ status }))
      renderAt()
      expect(await screen.findByRole('button', { name: 'Agregar sesión' })).toBeInTheDocument()
    },
  )
})

describe('EventDetailPage session management', () => {
  beforeEach(() => loginAs('organizer', 1))

  it('adds a session, confirms with a toast, closes the form and reloads the event', async () => {
    vi.mocked(sessionsApi.createSession).mockResolvedValue({ ...opening, id: 2 })
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Agregar sesión' }))
    fill({
      'Título de la sesión': 'Taller',
      'Inicio de la sesión': '2030-05-20T12:00',
      'Fin de la sesión': '2030-05-20T13:30',
      'Capacidad de la sesión': '40',
    })
    await pickSpeaker('Grace Hopper')
    fireEvent.click(screen.getByRole('button', { name: 'Agregar sesión' }))
    await waitFor(() => expect(toastMessages()).toContain('Sesión agregada'))
    expect(sessionsApi.createSession).toHaveBeenCalledWith(5, {
      title: 'Taller',
      speaker_id: 4,
      start_at: '2030-05-20T12:00:00.000Z',
      end_at: '2030-05-20T13:30:00.000Z',
      capacity: 40,
    })
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
    await waitFor(() =>
      expect(screen.queryByRole('form', { name: 'Formulario de sesión' })).not.toBeInTheDocument(),
    )
  })

  it('does not call the backend when the session form is invalid', async () => {
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Agregar sesión' }))
    fireEvent.click(screen.getByRole('button', { name: 'Agregar sesión' }))
    expect(await screen.findByText('El título es obligatorio')).toBeInTheDocument()
    expect(screen.getByText('Elige un ponente')).toBeInTheDocument()
    expect(sessionsApi.createSession).not.toHaveBeenCalled()
  })

  it('keeps the form open and shows the backend message when saving fails', async () => {
    vi.mocked(sessionsApi.createSession).mockRejectedValue(
      new ApiError('El ponente ya tiene una sesión en ese horario.', 409),
    )
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Agregar sesión' }))
    fill({
      'Título de la sesión': 'Taller',
      'Inicio de la sesión': '2030-05-20T12:00',
      'Fin de la sesión': '2030-05-20T13:30',
      'Capacidad de la sesión': '40',
    })
    await pickSpeaker('Grace Hopper')
    fireEvent.click(screen.getByRole('button', { name: 'Agregar sesión' }))
    const form = screen.getByRole('form', { name: 'Formulario de sesión' })
    expect(await within(form).findByRole('alert')).toHaveTextContent(
      'El ponente ya tiene una sesión en ese horario.',
    )
    expect(toastMessages()).toEqual([])
  })

  it('edits a session starting from its current values', async () => {
    vi.mocked(sessionsApi.updateSession).mockResolvedValue(opening)
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Editar sesión Apertura' }))
    expect(screen.getByLabelText('Título de la sesión')).toHaveValue('Apertura')
    expect(screen.getByLabelText('Inicio de la sesión')).toHaveValue('2030-05-20T10:00')
    expect(screen.getByLabelText('Capacidad de la sesión')).toHaveValue(20)
    expect(screen.getByText('Ada Lovelace', { selector: 'strong' })).toBeInTheDocument()
    fill({ 'Título de la sesión': 'Apertura general' })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar sesión' }))
    await waitFor(() => expect(toastMessages()).toContain('Sesión actualizada'))
    expect(sessionsApi.updateSession).toHaveBeenCalledWith(5, 1, {
      title: 'Apertura general',
      speaker_id: 3,
      start_at: '2030-05-20T10:00:00.000Z',
      end_at: '2030-05-20T11:00:00.000Z',
      capacity: 20,
    })
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })

  it('closes the form without saving when the user cancels', async () => {
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Agregar sesión' }))
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('form', { name: 'Formulario de sesión' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Agregar sesión' })).toBeInTheDocument()
  })

  it('links the form to the speaker creation page', async () => {
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Agregar sesión' }))
    expect(screen.getByRole('link', { name: 'Crear un ponente nuevo' })).toHaveAttribute(
      'href',
      '/speakers/new',
    )
  })

  it('deletes a session after confirming, with a toast and a reload', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(sessionsApi.deleteSession).mockResolvedValue()
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar sesión Apertura' }))
    await waitFor(() => expect(toastMessages()).toContain('Sesión eliminada'))
    expect(confirm).toHaveBeenCalledWith('¿Eliminar la sesión "Apertura"?')
    expect(sessionsApi.deleteSession).toHaveBeenCalledWith(5, 1)
    expect(eventsApi.getEvent).toHaveBeenCalledTimes(2)
  })

  it('keeps the session when the user does not confirm the deletion', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar sesión Apertura' }))
    expect(sessionsApi.deleteSession).not.toHaveBeenCalled()
  })

  it('shows the backend message in a toast when deleting fails', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(sessionsApi.deleteSession).mockRejectedValue(
      new ApiError('Sesión no encontrada.', 404),
    )
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Eliminar sesión Apertura' }))
    await waitFor(() => expect(toastMessages()).toContain('Sesión no encontrada.'))
  })
})
