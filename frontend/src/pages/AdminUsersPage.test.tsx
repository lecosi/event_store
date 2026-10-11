import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as adminApi from '../api/admin'
import * as authApi from '../api/auth'
import { ApiError } from '../api/client'
import { routes } from '../routes'
import { useAuthStore } from '../store/authStore'
import { useToastStore } from '../store/toastStore'
import type { Page, Role, User } from '../types'

vi.mock('../api/admin')
vi.mock('../api/auth')
vi.mock('../api/events')

const admin: User = {
  id: 1,
  email: 'ana@example.com',
  full_name: 'Ana Pérez',
  role: 'admin',
  is_active: true,
}
const beto: User = {
  id: 2,
  email: 'beto@example.com',
  full_name: 'Beto Gómez',
  role: 'attendee',
  is_active: true,
}
const carla: User = {
  id: 3,
  email: 'carla@example.com',
  full_name: 'Carla Ruiz',
  role: 'organizer',
  is_active: false,
}

const pageOf = (items: User[], page = 1, pages = 1): Page<User> => ({
  items,
  total: items.length,
  page,
  size: 10,
  pages,
})

function loginAs(role: Role) {
  useAuthStore.setState({ token: 'tok', user: { ...admin, role } })
}

function renderPage() {
  const router = createMemoryRouter(routes, { initialEntries: ['/admin/users'] })
  render(<RouterProvider router={router} />)
  return router
}

const toastMessages = () => useToastStore.getState().toasts.map((t) => t.message)
const rowOf = (name: string) => screen.getByText(name).closest('li') as HTMLElement

async function openEditor(name: string) {
  fireEvent.click(await screen.findByRole('button', { name: `Editar usuario ${name}` }))
  return screen.getByRole('form', { name: `Editar usuario ${name}` })
}

beforeEach(() => {
  vi.resetAllMocks()
  loginAs('admin')
  useToastStore.setState({ toasts: [] })
  vi.mocked(adminApi.listUsers).mockResolvedValue(pageOf([admin, beto, carla]))
})

describe('AdminUsersPage access', () => {
  it.each<Role>(['organizer', 'attendee'])(
    'tells an %s that they have no permission and loads nothing',
    async (role) => {
      loginAs(role)
      renderPage()
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'No tienes permiso para administrar usuarios.',
      )
      expect(adminApi.listUsers).not.toHaveBeenCalled()
    },
  )

  it('sends an anonymous visitor to the login page', async () => {
    useAuthStore.setState({ token: null, user: null })
    const router = renderPage()
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'))
  })
})

describe('AdminUsersPage list', () => {
  it('shows name, email, role and state of every user', async () => {
    renderPage()
    const row = (await screen.findByText('Beto Gómez')).closest('li') as HTMLElement
    expect(within(row).getByText('beto@example.com')).toBeInTheDocument()
    expect(within(row).getByText('Asistente')).toBeInTheDocument()
    expect(within(row).getByText('Activo')).toBeInTheDocument()
    expect(within(rowOf('Carla Ruiz')).getByText('Organizador')).toBeInTheDocument()
    expect(within(rowOf('Carla Ruiz')).getByText('Inactivo')).toBeInTheDocument()
    expect(adminApi.listUsers).toHaveBeenCalledWith({ page: 1, size: 10 })
  })

  it('shows a spinner while the users load', async () => {
    vi.mocked(adminApi.listUsers).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(await screen.findByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('shows the backend message when the users cannot be loaded', async () => {
    vi.mocked(adminApi.listUsers).mockRejectedValue(new ApiError('Servidor caído.', 500))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Servidor caído.')
  })

  it('shows an empty state when there are no users', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(pageOf([], 1, 0))
    renderPage()
    expect(await screen.findByText('Aún no hay usuarios.')).toBeInTheDocument()
  })

  it('loads the requested page with the pagination controls', async () => {
    vi.mocked(adminApi.listUsers).mockImplementation(async (params) =>
      params?.page === 2 ? pageOf([carla], 2, 2) : pageOf([beto], 1, 2),
    )
    renderPage()
    await screen.findByText('Beto Gómez')
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('Carla Ruiz')).toBeInTheDocument()
    expect(adminApi.listUsers).toHaveBeenLastCalledWith({ page: 2, size: 10 })
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()
  })

  it('ignores the response of a page the admin has already left', async () => {
    let resolveFirst: (page: Page<User>) => void = () => {}
    vi.mocked(adminApi.listUsers)
      .mockResolvedValueOnce(pageOf([beto], 1, 3))
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(pageOf([carla], 3, 3))
    renderPage()
    await screen.findByText('Beto Gómez')
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(await screen.findByText('Carla Ruiz')).toBeInTheDocument()
    await act(async () => resolveFirst(pageOf([{ ...beto, full_name: 'Usuario viejo' }], 2, 3)))
    expect(screen.queryByText('Usuario viejo')).not.toBeInTheDocument()
  })
})

describe('AdminUsersPage editing', () => {
  it('opens a form with the current values of the user', async () => {
    renderPage()
    const form = await openEditor('Beto Gómez')
    expect(within(form).getByLabelText('Nombre completo')).toHaveValue('Beto Gómez')
    expect(within(form).getByLabelText('Correo electrónico')).toHaveValue('beto@example.com')
    expect(within(form).getByLabelText('Rol')).toHaveValue('attendee')
    expect(within(form).getByLabelText('Cuenta activa')).toBeChecked()
  })

  it('edits one user at a time', async () => {
    renderPage()
    await openEditor('Beto Gómez')
    fireEvent.click(screen.getByRole('button', { name: 'Editar usuario Carla Ruiz' }))
    expect(
      screen.queryByRole('form', { name: 'Editar usuario Beto Gómez' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('form', { name: 'Editar usuario Carla Ruiz' })).toBeInTheDocument()
  })

  it('closes the form without saving when the admin cancels', async () => {
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.click(within(form).getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(adminApi.updateUser).not.toHaveBeenCalled()
  })

  it('sends only the fields that changed', async () => {
    vi.mocked(adminApi.updateUser).mockResolvedValue({ ...beto, role: 'organizer' })
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Rol'), { target: { value: 'organizer' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(adminApi.updateUser).toHaveBeenCalledWith(2, { role: 'organizer' }))
  })

  it('sends the trimmed name and the deactivation together', async () => {
    vi.mocked(adminApi.updateUser).mockResolvedValue(beto)
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Nombre completo'), {
      target: { value: '  Beto Gómez Díaz  ' },
    })
    fireEvent.click(within(form).getByLabelText('Cuenta activa'))
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() =>
      expect(adminApi.updateUser).toHaveBeenCalledWith(2, {
        full_name: 'Beto Gómez Díaz',
        is_active: false,
      }),
    )
  })

  it('says there is nothing to save and does not call the api', async () => {
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByText('No hay cambios para guardar.')).toBeInTheDocument()
    expect(adminApi.updateUser).not.toHaveBeenCalled()
  })

  it('does not call the api when the name is blank', async () => {
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Nombre completo'), { target: { value: '  ' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByText('El nombre completo es obligatorio')).toBeInTheDocument()
    expect(adminApi.updateUser).not.toHaveBeenCalled()
  })

  it('does not call the api when the email is invalid', async () => {
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Correo electrónico'), {
      target: { value: 'no-es-un-correo' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByText('Ingresa un correo electrónico válido')).toBeInTheDocument()
    expect(adminApi.updateUser).not.toHaveBeenCalled()
  })

  it('updates the row, confirms with a toast and closes the form on success', async () => {
    vi.mocked(adminApi.updateUser).mockResolvedValue({ ...beto, full_name: 'Alberto Gómez' })
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Nombre completo'), {
      target: { value: 'Alberto Gómez' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    expect(await screen.findByText('Alberto Gómez')).toBeInTheDocument()
    expect(screen.queryByText('Beto Gómez')).not.toBeInTheDocument()
    expect(toastMessages()).toContain('Usuario actualizado')
    expect(screen.queryByRole('form')).not.toBeInTheDocument()
    expect(adminApi.listUsers).toHaveBeenCalledTimes(1)
  })

  it('shows the backend message and keeps the form open when the email is taken', async () => {
    vi.mocked(adminApi.updateUser).mockRejectedValue(
      new ApiError('Este correo electrónico ya está registrado.', 409),
    )
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.change(within(form).getByLabelText('Correo electrónico'), {
      target: { value: 'carla@example.com' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    expect(await within(form).findByRole('alert')).toHaveTextContent(
      'Este correo electrónico ya está registrado.',
    )
    expect(screen.getByRole('form', { name: 'Editar usuario Beto Gómez' })).toBeInTheDocument()
  })

  it('disables the role and active controls on the own row and says why', async () => {
    renderPage()
    const form = await openEditor('Ana Pérez')
    expect(within(form).getByLabelText('Rol')).toBeDisabled()
    expect(within(form).getByLabelText('Cuenta activa')).toBeDisabled()
    expect(
      within(form).getByText('No puedes cambiar tu propio rol ni desactivar tu cuenta.'),
    ).toBeInTheDocument()
    expect(within(form).getByLabelText('Nombre completo')).toBeEnabled()
  })

  it('keeps the role and active controls enabled on another admin row', async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue(pageOf([admin, { ...beto, role: 'admin' }]))
    renderPage()
    const form = await openEditor('Beto Gómez')
    expect(within(form).getByLabelText('Rol')).toBeEnabled()
    expect(within(form).getByLabelText('Cuenta activa')).toBeEnabled()
  })

  it('refreshes the navbar name when the admin edits their own name', async () => {
    vi.mocked(adminApi.updateUser).mockResolvedValue({ ...admin, full_name: 'Ana María Pérez' })
    vi.mocked(authApi.fetchMe).mockResolvedValue({ ...admin, full_name: 'Ana María Pérez' })
    renderPage()
    const form = await openEditor('Ana Pérez')
    fireEvent.change(within(form).getByLabelText('Nombre completo'), {
      target: { value: 'Ana María Pérez' },
    })
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() =>
      expect(within(screen.getByRole('banner')).getByText('Ana María Pérez')).toBeInTheDocument(),
    )
    expect(adminApi.updateUser).toHaveBeenCalledWith(1, { full_name: 'Ana María Pérez' })
  })

  it('does not reload the own profile when another user is edited', async () => {
    vi.mocked(adminApi.updateUser).mockResolvedValue({ ...beto, is_active: false })
    renderPage()
    const form = await openEditor('Beto Gómez')
    fireEvent.click(within(form).getByLabelText('Cuenta activa'))
    fireEvent.click(within(form).getByRole('button', { name: 'Guardar cambios' }))
    await waitFor(() => expect(toastMessages()).toContain('Usuario actualizado'))
    expect(authApi.fetchMe).not.toHaveBeenCalled()
  })
})
