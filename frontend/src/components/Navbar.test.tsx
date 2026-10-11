import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '../store/authStore'
import type { Role, User } from '../types'
import { Navbar } from './Navbar'

function loggedInAs(role: Role) {
  const user: User = { id: 1, email: 'ana@example.com', role, is_active: true }
  useAuthStore.setState({ token: 'tok', user })
}

function renderNavbar() {
  return render(
    <MemoryRouter>
      <Navbar />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  useAuthStore.setState({ token: null, user: null })
})

describe('Navbar', () => {
  it('links to the home page from the brand', () => {
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Mis Eventos' })).toHaveAttribute('href', '/')
  })

  it('offers login and register when logged out', () => {
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Iniciar sesión' })).toHaveAttribute('href', '/login')
    expect(screen.getByRole('link', { name: 'Registrarse' })).toHaveAttribute('href', '/register')
    expect(screen.queryByRole('button', { name: 'Cerrar sesión' })).not.toBeInTheDocument()
  })

  it('shows profile, email and logout to an attendee without creation links', () => {
    loggedInAs('attendee')
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Mis eventos' })).toHaveAttribute('href', '/profile')
    expect(screen.getByText('ana@example.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cerrar sesión' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo evento' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Nuevo ponente' })).not.toBeInTheDocument()
  })

  it.each<Role>(['organizer', 'admin'])('shows the creation links to an %s', (role) => {
    loggedInAs(role)
    renderNavbar()
    expect(screen.getByRole('link', { name: 'Nuevo evento' })).toHaveAttribute('href', '/events/new')
    expect(screen.getByRole('link', { name: 'Nuevo ponente' })).toHaveAttribute('href', '/speakers/new')
  })

  it('logs the user out and shows the login links again', () => {
    loggedInAs('attendee')
    renderNavbar()
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }))
    expect(useAuthStore.getState().token).toBeNull()
    expect(screen.getByRole('link', { name: 'Iniciar sesión' })).toBeInTheDocument()
  })
})
