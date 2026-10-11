import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Select, TextArea } from './Fields'

describe('Select', () => {
  it('associates the label with the select', () => {
    render(
      <Select label="Estado">
        <option value="a">A</option>
      </Select>,
    )
    expect(screen.getByLabelText('Estado')).toBeInTheDocument()
  })

  it('does not flag the field as invalid without an error', () => {
    render(<Select label="Estado" />)
    expect(screen.getByLabelText('Estado')).not.toHaveAttribute('aria-invalid')
  })

  it('shows the error as an alert linked to the select', () => {
    render(<Select label="Estado" error="Elige un estado" />)
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Elige un estado')
    expect(screen.getByLabelText('Estado')).toHaveAttribute('aria-describedby', alert.id)
  })
})

describe('TextArea', () => {
  it('associates the label with the textarea', () => {
    render(<TextArea label="Descripción" />)
    expect(screen.getByLabelText('Descripción').tagName).toBe('TEXTAREA')
  })

  it('shows the error as an alert linked to the textarea', () => {
    render(<TextArea label="Descripción" error="Demasiado larga" />)
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Demasiado larga')
    expect(screen.getByLabelText('Descripción')).toHaveAttribute('aria-describedby', alert.id)
    expect(screen.getByLabelText('Descripción')).toHaveAttribute('aria-invalid', 'true')
  })
})
