import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import * as speakersApi from '../api/speakers'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import type { Role } from '../types'

vi.mock('../api/events')
vi.mock('../api/speakers')

function loginAs(role: Role) {
  useAuthStore.setState({
    token: 'tok',
    user: { id: 1, email: 'ana@example.com', full_name: 'Ana Pérez', role, is_active: true },
  })
}

function renderPage(entries = ['/speakers/new'], initialIndex = entries.length - 1) {
  const router = createMemoryRouter(routes, { initialEntries: entries, initialIndex })
  render(<RouterProvider router={router} />)
  return router
}

const toastMessages = () => useToastStore.getState().toasts.map((t) => t.message)

beforeEach(() => {
  vi.resetAllMocks()
  useAuthStore.setState({ token: null, user: null })
  useToastStore.setState({ toasts: [] })
  vi.mocked(eventsApi.listEvents).mockResolvedValue({
    items: [],
    total: 0,
    page: 1,
    size: 9,
    pages: 0,
  })
  vi.mocked(eventsApi.getEvent).mockRejectedValue(new ApiError('Evento no encontrado.', 404))
})

describe('SpeakerFormPage', () => {
  it('sends an anonymous visitor to the login page', async () => {
    const router = renderPage()
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it('shows a spinner while the profile of a logged-in user is not loaded yet', async () => {
    useAuthStore.setState({ token: 'tok', user: null })
    renderPage()
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('tells an attendee that only organizers and admins can create speakers', async () => {
    loginAs('attendee')
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No tienes permiso para crear ponentes.',
    )
    expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument()
  })

  it('creates the speaker, confirms with a toast and goes back to the previous page', async () => {
    loginAs('organizer')
    vi.mocked(speakersApi.createSpeaker).mockResolvedValue({
      id: 3,
      name: 'Grace Hopper',
      bio: '',
      email: null,
    })
    const router = renderPage(['/events/5', '/speakers/new'])
    fireEvent.change(await screen.findByLabelText('Nombre'), { target: { value: 'Grace Hopper' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear ponente' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/events/5'))
    expect(speakersApi.createSpeaker).toHaveBeenCalledWith({ name: 'Grace Hopper', bio: '' })
    expect(toastMessages()).toContain('Ponente "Grace Hopper" creado')
  })

  it('goes to the home page when there is no previous page to return to', async () => {
    loginAs('admin')
    vi.mocked(speakersApi.createSpeaker).mockResolvedValue({
      id: 3,
      name: 'Grace Hopper',
      bio: '',
      email: null,
    })
    const router = renderPage()
    fireEvent.change(await screen.findByLabelText('Nombre'), { target: { value: 'Grace Hopper' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear ponente' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })

  it('stays on the form and shows the backend message when creation fails', async () => {
    loginAs('organizer')
    vi.mocked(speakersApi.createSpeaker).mockRejectedValue(
      new ApiError('El ponente ya existe.', 500),
    )
    const router = renderPage()
    fireEvent.change(await screen.findByLabelText('Nombre'), { target: { value: 'Grace Hopper' } })
    fireEvent.click(screen.getByRole('button', { name: 'Crear ponente' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El ponente ya existe.')
    expect(router.state.location.pathname).toBe('/speakers/new')
    expect(toastMessages()).toEqual([])
  })
})
