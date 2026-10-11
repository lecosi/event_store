import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth'
import * as eventsApi from '../api/events'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'

vi.mock('../api/auth')
vi.mock('../api/events')

function renderRegister() {
  const router = createMemoryRouter(routes, { initialEntries: ['/register'] })
  render(<RouterProvider router={router} />)
  return router
}

function submit(fullName: string, email: string, password: string, confirmation: string) {
  fireEvent.change(screen.getByLabelText('Nombre completo'), { target: { value: fullName } })
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: password } })
  fireEvent.change(screen.getByLabelText('Confirmar contraseña'), {
    target: { value: confirmation },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }))
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

describe('RegisterPage', () => {
  it('shows the form with a link to login', async () => {
    renderRegister()
    expect(await screen.findByRole('heading', { name: 'Crear cuenta' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Inicia sesión' })).toHaveAttribute('href', '/login')
  })

  it('shows validation errors and does not call the backend with invalid data', async () => {
    renderRegister()
    await screen.findByRole('heading', { name: 'Crear cuenta' })
    submit('   ', 'ana', '123', '456')
    expect(await screen.findByText('El nombre completo es obligatorio')).toBeInTheDocument()
    expect(screen.getByText('Ingresa un correo electrónico válido')).toBeInTheDocument()
    expect(screen.getByText('La contraseña debe tener al menos 8 caracteres')).toBeInTheDocument()
    expect(screen.getByText('Las contraseñas no coinciden')).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
  })

  it('rejects a full name longer than 200 characters without calling the backend', async () => {
    renderRegister()
    await screen.findByRole('heading', { name: 'Crear cuenta' })
    submit('a'.repeat(201), 'ana@example.com', 'secret123', 'secret123')
    expect(
      await screen.findByText('El nombre completo debe tener como máximo 200 caracteres'),
    ).toBeInTheDocument()
    expect(authApi.register).not.toHaveBeenCalled()
  })

  it('creates the account, logs in and goes to the home page', async () => {
    vi.mocked(authApi.register).mockResolvedValue({
      id: 3,
      email: 'ana@example.com',
      full_name: 'Ana Pérez',
      role: 'organizer',
      is_active: true,
    })
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'tok', token_type: 'bearer' })
    vi.mocked(authApi.fetchMe).mockResolvedValue({
      id: 3,
      email: 'ana@example.com',
      full_name: 'Ana Pérez',
      role: 'organizer',
      is_active: true,
    })
    const router = renderRegister()
    await screen.findByRole('heading', { name: 'Crear cuenta' })
    submit('  Ana Pérez  ', ' ana@example.com ', 'secret123', 'secret123')
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
    expect(authApi.register).toHaveBeenCalledWith('ana@example.com', 'secret123', 'Ana Pérez')
    expect(authApi.login).toHaveBeenCalledWith('ana@example.com', 'secret123')
    expect(useAuthStore.getState().user?.full_name).toBe('Ana Pérez')
  })

  it('shows the backend message when the email is already registered', async () => {
    vi.mocked(authApi.register).mockRejectedValue(
      new ApiError('Este correo electrónico ya está registrado.', 409),
    )
    const router = renderRegister()
    await screen.findByRole('heading', { name: 'Crear cuenta' })
    submit('Ana Pérez', 'ana@example.com', 'secret123', 'secret123')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Este correo electrónico ya está registrado.',
    )
    expect(router.state.location.pathname).toBe('/register')
  })
})
