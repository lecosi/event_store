import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { EventStatus } from '../types'
import { StatusBadge } from './StatusBadge'

describe('StatusBadge', () => {
  it.each<[EventStatus, string]>([
    ['draft', 'Borrador'],
    ['published', 'Publicado'],
    ['cancelled', 'Cancelado'],
    ['finished', 'Finalizado'],
  ])('shows %s as %s', (status, label) => {
    render(<StatusBadge status={status} />)
    expect(screen.getByText(label)).toBeInTheDocument()
  })
})
