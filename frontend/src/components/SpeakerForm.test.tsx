import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { SpeakerForm } from './SpeakerForm'

function fill(values: Record<string, string>) {
  for (const [label, value] of Object.entries(values)) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  }
}

const submit = () => fireEvent.click(screen.getByRole('button', { name: 'Crear ponente' }))

describe('SpeakerForm', () => {
  it('shows validation errors and does not submit an invalid form', async () => {
    const onSubmit = vi.fn()
    render(<SpeakerForm onSubmit={onSubmit} />)
    fill({ 'Correo electrónico': 'no-es-un-correo' })
    submit()
    expect(await screen.findByText('El nombre es obligatorio')).toBeInTheDocument()
    expect(screen.getByText('Ingresa un correo electrónico válido')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits the trimmed name, the bio and the email', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<SpeakerForm onSubmit={onSubmit} />)
    fill({
      Nombre: '  Grace Hopper ',
      Biografía: 'Almirante',
      'Correo electrónico': 'grace@example.com',
    })
    submit()
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1))
    expect(onSubmit).toHaveBeenCalledWith({
      name: 'Grace Hopper',
      bio: 'Almirante',
      email: 'grace@example.com',
    })
  })

  it('leaves the email out of the payload when it is blank', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<SpeakerForm onSubmit={onSubmit} />)
    fill({ Nombre: 'Grace Hopper' })
    submit()
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith({ name: 'Grace Hopper', bio: '' }))
  })

  it('shows a taken email on the email field', async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(
        new ApiError('Este correo electrónico ya está en uso por otro ponente.', 409),
      )
    render(<SpeakerForm onSubmit={onSubmit} />)
    fill({ Nombre: 'Grace Hopper', 'Correo electrónico': 'grace@example.com' })
    submit()
    expect(
      await screen.findByText('Este correo electrónico ya está en uso por otro ponente.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Correo electrónico')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('button', { name: 'Crear ponente' })).toBeEnabled()
  })

  it('shows any other rejection above the form', async () => {
    render(<SpeakerForm onSubmit={vi.fn().mockRejectedValue(new ApiError('Sin permisos.', 403))} />)
    fill({ Nombre: 'Grace Hopper' })
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('Sin permisos.')
  })

  it('falls back to a generic message when the rejection is not an error', async () => {
    render(<SpeakerForm onSubmit={vi.fn().mockRejectedValue('boom')} />)
    fill({ Nombre: 'Grace Hopper' })
    submit()
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo crear el ponente')
  })
})
