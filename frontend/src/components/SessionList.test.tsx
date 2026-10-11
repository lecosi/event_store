process.env.TZ = 'UTC'

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Session } from '../types'
import { SessionList } from './SessionList'

const session = (id: number, title: string, start_at: string): Session => ({
  id,
  event_id: 5,
  title,
  start_at,
  end_at: '2030-05-20T18:00:00Z',
  capacity: 20,
  speaker: { id: 1, name: 'Ada Lovelace' },
})

const closing = session(2, 'Cierre', '2030-05-20T16:00:00Z')
const opening = session(1, 'Apertura', '2030-05-20T10:00:00Z')

describe('SessionList', () => {
  it('shows a message when there are no sessions', () => {
    render(<SessionList sessions={[]} />)
    expect(screen.getByText('Aún no hay sesiones programadas.')).toBeInTheDocument()
  })

  it('orders the sessions by start time and shows speaker and seats', () => {
    render(<SessionList sessions={[closing, opening]} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Apertura')
    expect(items[0]).toHaveTextContent('Ada Lovelace')
    expect(items[0]).toHaveTextContent('20 cupos')
    expect(items[1]).toHaveTextContent('Cierre')
  })

  it('uses the singular when a session has a single seat', () => {
    render(<SessionList sessions={[{ ...opening, capacity: 1 }]} />)
    expect(screen.getByRole('listitem')).toHaveTextContent('1 cupo')
    expect(screen.getByRole('listitem')).not.toHaveTextContent('1 cupos')
  })

  it('does not show actions without handlers', () => {
    render(<SessionList sessions={[opening]} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('calls the handlers with the session of the clicked row', () => {
    const onEdit = vi.fn()
    const onDelete = vi.fn()
    render(<SessionList sessions={[opening, closing]} onEdit={onEdit} onDelete={onDelete} />)
    fireEvent.click(screen.getByRole('button', { name: 'Editar sesión Cierre' }))
    fireEvent.click(screen.getByRole('button', { name: 'Eliminar sesión Apertura' }))
    expect(onEdit).toHaveBeenCalledWith(closing)
    expect(onDelete).toHaveBeenCalledWith(opening)
  })

  it('disables the actions while busy', () => {
    render(<SessionList sessions={[opening]} onEdit={vi.fn()} onDelete={vi.fn()} busy />)
    expect(screen.getByRole('button', { name: 'Editar sesión Apertura' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Eliminar sesión Apertura' })).toBeDisabled()
  })
})
