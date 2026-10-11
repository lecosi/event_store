import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { routes } from '.'
import { useAuthStore } from '../store/authStore'

beforeEach(() => {
  useAuthStore.setState({ token: null, user: null })
})

describe('routes', () => {
  it('shows the not found page inside the layout for an unknown path', async () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/does-not-exist'] })
    render(<RouterProvider router={router} />)
    expect(await screen.findByRole('heading', { name: 'Página no encontrada' })).toBeInTheDocument()
    expect(screen.getByRole('banner')).toBeInTheDocument()
  })

  it('links back to the home page from the not found page', async () => {
    const router = createMemoryRouter(routes, { initialEntries: ['/does-not-exist'] })
    render(<RouterProvider router={router} />)
    expect(await screen.findByRole('link', { name: 'Volver al inicio' })).toHaveAttribute(
      'href',
      '/',
    )
  })

  it('lands on the home page when logging out from a protected page', async () => {
    useAuthStore.setState({
      token: 'tok',
      user: { id: 1, email: 'a@b.co', full_name: 'Ana', role: 'organizer', is_active: true },
    })
    const router = createMemoryRouter(routes, { initialEntries: ['/events/new'] })
    render(<RouterProvider router={router} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Cerrar sesión' }))
    await screen.findByRole('link', { name: 'Iniciar sesión' })
    expect(router.state.location.pathname).toBe('/')
  })
})
