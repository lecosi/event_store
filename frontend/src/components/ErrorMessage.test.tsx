import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ErrorMessage } from './ErrorMessage'

describe('ErrorMessage', () => {
  it('shows the message as an alert', () => {
    render(<ErrorMessage message="No se pudo guardar" />)
    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo guardar')
  })

  it('renders nothing when there is no message', () => {
    const { container } = render(<ErrorMessage message={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
