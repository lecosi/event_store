process.env.TZ = 'UTC'

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { EventPayload } from '../types'
import { EventForm } from './EventForm'

const initial: EventPayload = {
  name: 'PyCon',
  description: 'Charlas',
  location: 'Medellín',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:30:00Z',
  capacity: 80,
}

function fill(values: Record<string, string>) {
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
}

const validValues = {
  Nombre: '  Taller de React  ',
  Lugar: ' Bogotá ',
  Inicio: '2999-01-01T10:00',
  Fin: '2999-01-01T12:00',
  Capacidad: '25',
}

describe('EventForm', () => {
  it('starts empty when creating', () => {
    render(<EventForm submitLabel="Crear evento" requireFutureStart onSubmit={vi.fn()} />)
    expect(screen.getByLabelText('Nombre')).toHaveValue('')
    expect(screen.getByLabelText('Capacidad')).toHaveValue(null)
  })

  it('is prefilled from the initial event when editing', () => {
    render(
      <EventForm
        initial={initial}
        submitLabel="Guardar"
        requireFutureStart={false}
        onSubmit={vi.fn()}
      />,
    )
    expect(screen.getByLabelText('Nombre')).toHaveValue('PyCon')
    expect(screen.getByLabelText('Descripción')).toHaveValue('Charlas')
    expect(screen.getByLabelText('Lugar')).toHaveValue('Medellín')
    expect(screen.getByLabelText('Inicio')).toHaveValue('2030-05-20T09:00')
    expect(screen.getByLabelText('Fin')).toHaveValue('2030-05-21T18:30')
    expect(screen.getByLabelText('Capacidad')).toHaveValue(80)
  })

  it('shows validation errors and does not submit an invalid form', async () => {
    const onSubmit = vi.fn()
    render(<EventForm submitLabel="Crear evento" requireFutureStart onSubmit={onSubmit} />)
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    expect(await screen.findByText('El nombre es obligatorio')).toBeInTheDocument()
    expect(screen.getByText('El lugar es obligatorio')).toBeInTheDocument()
    expect(screen.getByText('La fecha de inicio es obligatoria')).toBeInTheDocument()
    expect(
      screen.getByText('La capacidad debe ser un número entero de al menos 1'),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits the trimmed values with UTC ISO dates and a numeric capacity', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<EventForm submitLabel="Crear evento" requireFutureStart onSubmit={onSubmit} />)
    fill(validValues)
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Taller de React',
      description: '',
      location: 'Bogotá',
      start_at: '2999-01-01T10:00:00.000Z',
      end_at: '2999-01-01T12:00:00.000Z',
      capacity: 25,
    })
  })

  it('does not require a future start when editing', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(
      <EventForm
        initial={{ ...initial, start_at: '2000-01-01T09:00:00Z', end_at: '2000-01-01T10:00:00Z' }}
        submitLabel="Guardar"
        requireFutureStart={false}
        onSubmit={onSubmit}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalled())
  })

  it('shows the message of a rejected submit and enables the button again', async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error('El evento no se puede editar.'))
    render(<EventForm submitLabel="Crear evento" requireFutureStart onSubmit={onSubmit} />)
    fill(validValues)
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('El evento no se puede editar.')
    expect(screen.getByRole('button', { name: 'Crear evento' })).toBeEnabled()
  })

  it('disables the button while the submit is in flight', async () => {
    let finish!: () => void
    const onSubmit = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)))
    render(<EventForm submitLabel="Crear evento" requireFutureStart onSubmit={onSubmit} />)
    fill(validValues)
    fireEvent.click(screen.getByRole('button', { name: 'Crear evento' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Crear evento' })).toBeDisabled())
    finish()
  })
})
