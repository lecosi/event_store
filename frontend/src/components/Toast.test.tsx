import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { toast, useToastStore } from '../store/toastStore'
import { ToastContainer } from './Toast'

beforeEach(() => {
  useToastStore.setState({ toasts: [] })
})

afterEach(() => {
  vi.useRealTimers()
})

describe('ToastContainer', () => {
  it('renders nothing but the live region when there are no toasts', () => {
    render(<ToastContainer />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows a success toast as a status message', () => {
    render(<ToastContainer />)
    act(() => toast.success('Evento creado'))
    expect(screen.getByRole('status')).toHaveTextContent('Evento creado')
  })

  it('shows an error toast as an alert', () => {
    render(<ToastContainer />)
    act(() => toast.error('No se pudo guardar'))
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo guardar')
  })

  it('removes a toast when its close button is pressed', () => {
    render(<ToastContainer />)
    act(() => toast.success('Evento creado'))
    fireEvent.click(screen.getByRole('button', { name: 'Cerrar' }))
    expect(screen.queryByText('Evento creado')).not.toBeInTheDocument()
  })

  it('removes a toast by itself after a few seconds', () => {
    vi.useFakeTimers()
    render(<ToastContainer />)
    act(() => toast.success('Evento creado'))
    expect(screen.getByText('Evento creado')).toBeInTheDocument()
    act(() => {
      vi.advanceTimersByTime(4000)
    })
    expect(screen.queryByText('Evento creado')).not.toBeInTheDocument()
  })
})
