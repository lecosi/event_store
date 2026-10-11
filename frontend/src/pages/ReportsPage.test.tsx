import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import * as reportsApi from '../api/reports'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import type { Page, Participant, Role } from '../types'

vi.mock('../api/reports')
vi.mock('../api/events')

const ana: Participant = { full_name: 'Ana Pérez', email: 'ana@example.com', event_name: 'PyCon' }
const beto: Participant = { full_name: 'Beto Gómez', email: 'beto@example.com', event_name: 'Rust' }

const pageOf = (items: Participant[], page = 1, pages = 1): Page<Participant> => ({
  items,
  total: items.length,
  page,
  size: 10,
  pages,
})

function loginAs(role: Role) {
  useAuthStore.setState({
    token: 'tok',
    user: { id: 1, email: 'o@example.com', full_name: 'Olga', role, is_active: true },
  })
}

function renderAt(url = '/reports') {
  const router = createMemoryRouter(routes, { initialEntries: [url] })
  render(<RouterProvider router={router} />)
  return router
}

const toastMessages = () => useToastStore.getState().toasts.map((t) => t.message)
const searchOf = (router: ReturnType<typeof renderAt>) =>
  new URLSearchParams(router.state.location.search)

beforeEach(() => {
  vi.resetAllMocks()
  loginAs('organizer')
  useToastStore.setState({ toasts: [] })
  vi.mocked(reportsApi.listParticipants).mockResolvedValue(pageOf([ana, beto]))
})

describe('ReportsPage access', () => {
  it('tells an attendee that they have no permission and loads nothing', async () => {
    loginAs('attendee')
    renderAt()
    expect(await screen.findByRole('alert')).toHaveTextContent('No tienes permiso para ver')
    expect(reportsApi.listParticipants).not.toHaveBeenCalled()
  })

  it('sends an anonymous visitor to the login page', async () => {
    useAuthStore.setState({ token: null, user: null })
    const router = renderAt()
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })

  it.each<Role>(['organizer', 'admin'])('lets an %s see the report', async (role) => {
    loginAs(role)
    renderAt()
    expect(await screen.findByText('Ana Pérez')).toBeInTheDocument()
  })
})

describe('ReportsPage list', () => {
  it('shows name, email and event of every participant', async () => {
    renderAt()
    const table = await screen.findByRole('table', { name: 'Participantes' })
    const row = within(table).getByText('Beto Gómez').closest('tr') as HTMLElement
    expect(within(row).getByText('beto@example.com')).toBeInTheDocument()
    expect(within(row).getByText('Rust')).toBeInTheDocument()
    expect(within(table).getAllByRole('columnheader')).toHaveLength(3)
    expect(reportsApi.listParticipants).toHaveBeenCalledWith({ page: 1, size: 10 })
  })

  it('shows a spinner while the report loads', async () => {
    vi.mocked(reportsApi.listParticipants).mockReturnValue(new Promise(() => {}))
    renderAt()
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('shows the backend message when the report cannot be loaded', async () => {
    vi.mocked(reportsApi.listParticipants).mockRejectedValue(new ApiError('Servidor caído.', 500))
    renderAt()
    expect(await screen.findByRole('alert')).toHaveTextContent('Servidor caído.')
  })

  it('shows an empty state when nobody matches', async () => {
    vi.mocked(reportsApi.listParticipants).mockResolvedValue(pageOf([], 1, 0))
    renderAt()
    expect(await screen.findByText('No hay participantes con estos filtros.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('ignores a response that arrives after the filters changed', async () => {
    let resolveFirst: (value: Page<Participant>) => void = () => {}
    vi.mocked(reportsApi.listParticipants)
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(pageOf([beto]))
    renderAt()
    fireEvent.change(await screen.findByLabelText('Estado'), { target: { value: 'draft' } })
    expect(await screen.findByText('Beto Gómez')).toBeInTheDocument()
    await act(async () => resolveFirst(pageOf([ana])))
    expect(screen.queryByText('Ana Pérez')).not.toBeInTheDocument()
    expect(screen.getByText('Beto Gómez')).toBeInTheDocument()
  })
})

describe('ReportsPage pagination', () => {
  it('requests the page in the URL', async () => {
    vi.mocked(reportsApi.listParticipants).mockResolvedValue(pageOf([beto], 2, 3))
    renderAt('/reports?page=2')
    await screen.findByText('Beto Gómez')
    expect(reportsApi.listParticipants).toHaveBeenCalledWith({ page: 2, size: 10 })
    expect(screen.getByText('Página 2 de 3')).toBeInTheDocument()
  })

  it('goes to the next page and keeps it in the URL', async () => {
    vi.mocked(reportsApi.listParticipants).mockResolvedValue(pageOf([ana], 1, 2))
    const router = renderAt('/reports?status=draft')
    fireEvent.click(await screen.findByRole('button', { name: 'Siguiente' }))
    await waitFor(() =>
      expect(reportsApi.listParticipants).toHaveBeenLastCalledWith({
        status: 'draft',
        page: 2,
        size: 10,
      }),
    )
    expect(searchOf(router).get('page')).toBe('2')
    expect(searchOf(router).get('status')).toBe('draft')
  })
})

describe('ReportsPage filters', () => {
  it('reads every filter from the URL', async () => {
    renderAt('/reports?q=py&status=published&date_from=2030-01-01&date_to=2030-02-01&event_id=5')
    await screen.findByText('Ana Pérez')
    expect(reportsApi.listParticipants).toHaveBeenCalledWith({
      q: 'py',
      status: 'published',
      date_from: '2030-01-01',
      date_to: '2030-02-01',
      event_id: 5,
      page: 1,
      size: 10,
    })
    expect(screen.getByLabelText('Estado')).toHaveValue('published')
    expect(screen.getByLabelText('Evento desde')).toHaveValue('2030-01-01')
    expect(screen.getByLabelText('Evento hasta')).toHaveValue('2030-02-01')
  })

  it('puts the status in the URL and goes back to the first page', async () => {
    const router = renderAt('/reports?page=3')
    fireEvent.change(await screen.findByLabelText('Estado'), { target: { value: 'cancelled' } })
    await waitFor(() =>
      expect(reportsApi.listParticipants).toHaveBeenLastCalledWith({
        status: 'cancelled',
        page: 1,
        size: 10,
      }),
    )
    expect(searchOf(router).get('status')).toBe('cancelled')
    expect(searchOf(router).has('page')).toBe(false)
  })

  it('removes the status from the URL when all statuses are chosen', async () => {
    const router = renderAt('/reports?status=draft')
    fireEvent.change(await screen.findByLabelText('Estado'), { target: { value: '' } })
    await waitFor(() => expect(searchOf(router).has('status')).toBe(false))
  })

  it('puts the dates in the URL', async () => {
    const router = renderAt()
    fireEvent.change(await screen.findByLabelText('Evento desde'), {
      target: { value: '2030-03-01' },
    })
    fireEvent.change(screen.getByLabelText('Evento hasta'), { target: { value: '2030-03-31' } })
    await waitFor(() => expect(searchOf(router).get('date_to')).toBe('2030-03-31'))
    expect(searchOf(router).get('date_from')).toBe('2030-03-01')
  })

  it('puts the search text in the URL after the user stops typing', async () => {
    const router = renderAt()
    fireEvent.change(await screen.findByRole('searchbox'), { target: { value: 'rust' } })
    await waitFor(() => expect(searchOf(router).get('q')).toBe('rust'))
    expect(reportsApi.listParticipants).toHaveBeenLastCalledWith({ q: 'rust', page: 1, size: 10 })
  })

  it('shows an error and loads nothing when the end date is before the start date', async () => {
    renderAt('/reports?date_from=2030-02-01&date_to=2030-01-01')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La fecha final no puede ser anterior a la fecha inicial.',
    )
    expect(reportsApi.listParticipants).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Descargar CSV' })).toBeDisabled()
  })

  it('shows the event filter and removes it on request', async () => {
    const router = renderAt('/reports?event_id=5&status=draft')
    expect(await screen.findByText('Solo participantes del evento 5')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Quitar filtro de evento' }))
    await waitFor(() => expect(searchOf(router).has('event_id')).toBe(false))
    expect(searchOf(router).get('status')).toBe('draft')
    expect(screen.queryByText('Solo participantes del evento 5')).not.toBeInTheDocument()
  })

  it('ignores an event id that is not a number', async () => {
    renderAt('/reports?event_id=abc')
    await screen.findByText('Ana Pérez')
    expect(reportsApi.listParticipants).toHaveBeenCalledWith({ page: 1, size: 10 })
  })
})

describe('ReportsPage download', () => {
  it('downloads with the current filters and without pagination', async () => {
    vi.mocked(reportsApi.downloadParticipantsCsv).mockResolvedValue()
    renderAt('/reports?q=py&status=published&date_from=2030-01-01&event_id=5&page=2')
    fireEvent.click(await screen.findByRole('button', { name: 'Descargar CSV' }))
    await waitFor(() => expect(toastMessages()).toContain('Reporte descargado'))
    expect(reportsApi.downloadParticipantsCsv).toHaveBeenCalledWith({
      q: 'py',
      status: 'published',
      date_from: '2030-01-01',
      event_id: 5,
    })
  })

  it('disables the button while the file is being downloaded', async () => {
    let finish: () => void = () => {}
    vi.mocked(reportsApi.downloadParticipantsCsv).mockReturnValue(
      new Promise<void>((resolve) => (finish = resolve)),
    )
    renderAt()
    const button = await screen.findByRole('button', { name: 'Descargar CSV' })
    fireEvent.click(button)
    await waitFor(() => expect(button).toBeDisabled())
    await act(async () => finish())
    await waitFor(() => expect(button).toBeEnabled())
  })

  it('shows the backend message in a toast when the download fails', async () => {
    vi.mocked(reportsApi.downloadParticipantsCsv).mockRejectedValue(
      new ApiError('Evento no encontrado.', 404),
    )
    renderAt()
    fireEvent.click(await screen.findByRole('button', { name: 'Descargar CSV' }))
    await waitFor(() => expect(toastMessages()).toContain('Evento no encontrado.'))
  })
})
