import { act, render, screen } from '@testing-library/react'
import { lazy } from 'react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { toast, useToastStore } from '../store/toastStore'
import { Layout } from './Layout'

function renderLayout(page: React.ReactNode) {
  const router = createMemoryRouter([{ element: <Layout />, children: [{ path: '/', element: page }] }])
  return render(<RouterProvider router={router} />)
}

beforeEach(() => {
  useToastStore.setState({ toasts: [] })
})

describe('Layout', () => {
  it('shows the navbar and the active page', () => {
    renderLayout(<p>Contenido</p>)
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveTextContent('Contenido')
  })

  it('shows a spinner while a lazy page is loading', async () => {
    let finish: (module: { default: () => React.ReactNode }) => void = () => {}
    const Lazy = lazy(
      () => new Promise<{ default: () => React.ReactNode }>((resolve) => (finish = resolve)),
    )
    renderLayout(<Lazy />)
    expect(screen.getByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
    await act(async () => finish({ default: () => <p>Cargada</p> }))
    expect(await screen.findByText('Cargada')).toBeInTheDocument()
  })

  it('shows toasts pushed from anywhere in the app', () => {
    renderLayout(<p>Contenido</p>)
    act(() => toast.success('Guardado'))
    expect(screen.getByText('Guardado')).toBeInTheDocument()
  })
})
