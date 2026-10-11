process.env.TZ = 'UTC'

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as speakersApi from '../api/speakers'
import type { Session } from '../types'
import { SessionForm } from './SessionForm'

vi.mock('../api/speakers')

const event = { start_at: '2030-05-20T09:00:00Z', end_at: '2030-05-21T18:00:00Z', capacity: 100 }

const session: Session = {
  id: 1,
  event_id: 5,
  title: 'Apertura',
  start_at: '2030-05-20T10:00:00Z',
  end_at: '2030-05-20T11:00:00Z',
  capacity: 20,
  speaker: { id: 3, name: 'Ada Lovelace' },
}

function renderForm(props: Partial<React.ComponentProps<typeof SessionForm>> = {}) {
  const onSubmit = vi.fn().mockResolvedValue(undefined)
  const onCancel = vi.fn()
  render(
    <MemoryRouter>
      <SessionForm event={event} onSubmit={onSubmit} onCancel={onCancel} {...props} />
    </MemoryRouter>,
  )
  return { onSubmit, onCancel }
}

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(speakersApi.listSpeakers).mockResolvedValue({
    items: [{ id: 4, name: 'Grace Hopper', bio: '', email: null }],
    total: 1,
    page: 1,
    size: 10,
    pages: 1,
  })
})

describe('SessionForm', () => {
  it('starts empty when adding', () => {
    renderForm()
    expect(screen.getByLabelText('Título de la sesión')).toHaveValue('')
    expect(screen.getByLabelText('Capacidad de la sesión')).toHaveValue(null)
    expect(screen.getByRole('button', { name: 'Agregar sesión' })).toBeInTheDocument()
  })

  it('is prefilled from the session when editing', () => {
    renderForm({ session })
    expect(screen.getByLabelText('Título de la sesión')).toHaveValue('Apertura')
    expect(screen.getByLabelText('Fin de la sesión')).toHaveValue('2030-05-20T11:00')
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Guardar sesión' })).toBeInTheDocument()
  })

  it('submits the chosen speaker with the trimmed title and UTC dates', async () => {
    const { onSubmit } = renderForm()
    fireEvent.change(screen.getByLabelText('Título de la sesión'), { target: { value: ' Taller ' } })
    fireEvent.change(screen.getByLabelText('Inicio de la sesión'), {
      target: { value: '2030-05-20T12:00' },
    })
    fireEvent.change(screen.getByLabelText('Fin de la sesión'), {
      target: { value: '2030-05-20T13:00' },
    })
    fireEvent.change(screen.getByLabelText('Capacidad de la sesión'), { target: { value: '30' } })
    fireEvent.focus(screen.getByLabelText('Ponente'))
    fireEvent.click(await screen.findByRole('button', { name: 'Grace Hopper' }))
    fireEvent.click(screen.getByRole('button', { name: 'Agregar sesión' }))
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({
      title: 'Taller',
      speaker_id: 4,
      start_at: '2030-05-20T12:00:00.000Z',
      end_at: '2030-05-20T13:00:00.000Z',
      capacity: 30,
    })
  })

  it('rejects a capacity above the event capacity', async () => {
    const { onSubmit } = renderForm({ session })
    fireEvent.change(screen.getByLabelText('Capacidad de la sesión'), { target: { value: '101' } })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar sesión' }))
    expect(
      await screen.findByText('La capacidad no puede superar la del evento (100)'),
    ).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('falls back to a generic message when the rejection is not an error', async () => {
    renderForm({ session, onSubmit: vi.fn().mockRejectedValue('boom') })
    fireEvent.click(screen.getByRole('button', { name: 'Guardar sesión' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar la sesión')
  })

  it('calls onCancel from the cancel button', () => {
    const { onCancel } = renderForm()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(onCancel).toHaveBeenCalled()
  })
})
