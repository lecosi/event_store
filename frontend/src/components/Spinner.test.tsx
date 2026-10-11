import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Spinner } from './Spinner'

describe('Spinner', () => {
  it('announces the default loading label', () => {
    render(<Spinner />)
    expect(screen.getByRole('status', { name: 'Cargando...' })).toBeInTheDocument()
  })

  it('announces a custom label', () => {
    render(<Spinner label="Buscando..." />)
    expect(screen.getByRole('status', { name: 'Buscando...' })).toBeInTheDocument()
  })
})
