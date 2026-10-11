import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { routes } from '.'

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
})
