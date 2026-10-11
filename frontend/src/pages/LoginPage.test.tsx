import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth'
import * as eventsApi from '../api/events'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import type { Role } from '../types'

vi.mock('../api/auth')
vi.mock('../api/events')

function renderLogin(state?: unknown) {
  const router = createMemoryRouter(routes, { initialEntries: [{ pathname: '/login', state }] })
  render(<RouterProvider router={router} />)
  return router
}

function submit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
}

function backendAcceptsLogin(role: Role = 'organizer') {
  vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
  vi.mocked(authApi.fetchMe).mockResolvedValue({
    id: 1,
    email: 'ana@example.com',
    role,
    is_active: true,
  })
}

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

describe('LoginPage', () => {
  it('shows the form with a link to register', async () => {
    renderLogin()
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Regístrate' })).toHaveAttribute('href', '/register')
  })

  it('shows validation errors and does not call the backend with invalid data', async () => {
    renderLogin()
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    submit('no-es-correo', '123')
    expect(await screen.findByText('Ingresa un correo electrónico válido')).toBeInTheDocument()
    expect(screen.getByText('La contraseña debe tener al menos 8 caracteres')).toBeInTheDocument()
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('logs in with the trimmed email and goes to the home page', async () => {
    backendAcceptsLogin()
    const router = renderLogin()
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    submit(' ana@example.com ', 'secret123')
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
    expect(authApi.login).toHaveBeenCalledWith('ana@example.com', 'secret123')
    expect(useAuthStore.getState().token).toBe('tok')
  })

  it('returns to the page the user came from', async () => {
    backendAcceptsLogin()
    const router = renderLogin({ from: { pathname: '/events/new', search: '' } })
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    submit('ana@example.com', 'secret123')
    await waitFor(() => expect(router.state.location.pathname).toBe('/events/new'))
  })

  it('keeps the query string of the page the user came from', async () => {
    backendAcceptsLogin()
    const router = renderLogin({ from: { pathname: '/', search: '?q=react' } })
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    submit('ana@example.com', 'secret123')
    await waitFor(() => expect(router.state.location.search).toBe('?q=react'))
  })

  it('shows the backend message when the credentials are wrong', async () => {
    vi.mocked(authApi.login).mockRejectedValue(
      new ApiError('Correo electrónico o contraseña incorrectos.', 401),
    )
    const router = renderLogin()
    await screen.findByRole('heading', { name: 'Iniciar sesión' })
    submit('ana@example.com', 'secret123')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Correo electrónico o contraseña incorrectos.',
    )
    expect(router.state.location.pathname).toBe('/login')
    expect(screen.getByRole('button', { name: 'Iniciar sesión' })).toBeEnabled()
  })
})
