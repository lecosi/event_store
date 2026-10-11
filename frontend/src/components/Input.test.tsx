import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Input } from './Input'

describe('Input', () => {
  it('associates the label with the input', () => {
    render(<Input label="Correo electrónico" />)
    expect(screen.getByLabelText('Correo electrónico')).toBeInTheDocument()
  })

  it('does not flag the field as invalid without an error', () => {
    render(<Input label="Nombre" />)
    expect(screen.getByLabelText('Nombre')).not.toHaveAttribute('aria-invalid')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the error as an alert linked to the input', () => {
    render(<Input label="Nombre" error="El nombre es obligatorio" />)
    const input = screen.getByLabelText('Nombre')
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('El nombre es obligatorio')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', alert.id)
  })

  it('uses the id given by the caller', () => {
    render(<Input label="Nombre" id="name-field" />)
    expect(screen.getByLabelText('Nombre')).toHaveAttribute('id', 'name-field')
  })

  it('passes native attributes to the input', () => {
    render(<Input label="Contraseña" type="password" placeholder="mínimo 8" />)
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password')
    expect(screen.getByPlaceholderText('mínimo 8')).toBeInTheDocument()
  })
})
