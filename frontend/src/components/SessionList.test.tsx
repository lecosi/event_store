process.env.TZ = 'UTC'

import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Session } from '../types'
import { SessionList, type SessionEnrollment } from './SessionList'

const session = (id: number, title: string, start_at: string): Session => ({
  id,
  event_id: 5,
  title,
  start_at,
  end_at: '2030-05-20T18:00:00Z',
  capacity: 20,
  speaker: { id: 1, name: 'Ada Lovelace' },
  enrolled_count: 5,
  available_spots: 15,
  is_enrolled: false,
})

const closing = session(2, 'Cierre', '2030-05-20T16:00:00Z')
const opening = session(1, 'Apertura', '2030-05-20T10:00:00Z')

describe('SessionList', () => {
  it('shows a message when there are no sessions', () => {
    render(<SessionList sessions={[]} />)
    expect(screen.getByText('Aún no hay sesiones programadas.')).toBeInTheDocument()
  })

  it('orders the sessions by start time and shows speaker and free spots', () => {
    render(<SessionList sessions={[closing, opening]} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Apertura')
    expect(items[0]).toHaveTextContent('Ada Lovelace')
    expect(items[0]).toHaveTextContent('Cupos disponibles: 15 de 20')
    expect(items[1]).toHaveTextContent('Cierre')
  })

  it('does not show actions without handlers', () => {
    render(<SessionList sessions={[opening]} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('tells the user which session they are enrolled in', () => {
    render(<SessionList sessions={[{ ...opening, is_enrolled: true }, closing]} />)
    const items = screen.getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Estás inscrito')
    expect(items[1]).not.toHaveTextContent('Estás inscrito')
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

  describe('enrollment', () => {
    const enrollment = (overrides: Partial<SessionEnrollment> = {}): SessionEnrollment => ({
      eventStatus: 'published',
      isRegisteredToEvent: true,
      onEnroll: vi.fn(),
      onCancel: vi.fn(),
      ...overrides,
    })

    it('calls onEnroll with the session when the user can enroll', () => {
      const options = enrollment()
      render(<SessionList sessions={[opening, closing]} enrollment={options} />)
      fireEvent.click(screen.getByRole('button', { name: 'Inscribirme en la sesión Cierre' }))
      expect(options.onEnroll).toHaveBeenCalledWith(closing)
    })

    it('calls onCancel instead of offering to enroll when the user is enrolled', () => {
      const options = enrollment()
      const enrolled = { ...opening, is_enrolled: true }
      render(<SessionList sessions={[enrolled]} enrollment={options} />)
      expect(
        screen.queryByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
      ).not.toBeInTheDocument()
      fireEvent.click(
        screen.getByRole('button', { name: 'Cancelar inscripción en la sesión Apertura' }),
      )
      expect(options.onCancel).toHaveBeenCalledWith(enrolled)
    })

    it('disables enrolling and asks to register to the event first', () => {
      render(
        <SessionList
          sessions={[opening]}
          enrollment={enrollment({ isRegisteredToEvent: false })}
        />,
      )
      expect(
        screen.getByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
      ).toBeDisabled()
      expect(
        screen.getByText('Inscríbete al evento para poder inscribirte en sus sesiones.'),
      ).toBeInTheDocument()
    })

    it('disables enrolling in a full session and says it is full', () => {
      render(
        <SessionList sessions={[{ ...opening, available_spots: 0 }]} enrollment={enrollment()} />,
      )
      expect(
        screen.getByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
      ).toBeDisabled()
      expect(screen.getByText('Esta sesión está llena.')).toBeInTheDocument()
    })

    it('keeps cancelling enabled in a full session the user is enrolled in', () => {
      render(
        <SessionList
          sessions={[{ ...opening, available_spots: 0, is_enrolled: true }]}
          enrollment={enrollment()}
        />,
      )
      expect(
        screen.getByRole('button', { name: 'Cancelar inscripción en la sesión Apertura' }),
      ).toBeEnabled()
    })

    it.each(['draft', 'cancelled', 'finished'] as const)(
      'disables enrolling when the event is %s',
      (eventStatus) => {
        render(<SessionList sessions={[opening]} enrollment={enrollment({ eventStatus })} />)
        expect(
          screen.getByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
        ).toBeDisabled()
        expect(screen.getByText(/las inscripciones a sesiones están cerradas/)).toBeInTheDocument()
      },
    )

    it('disables cancelling when the event is finished and says why', () => {
      render(
        <SessionList
          sessions={[{ ...opening, is_enrolled: true }]}
          enrollment={enrollment({ eventStatus: 'finished' })}
        />,
      )
      expect(
        screen.getByRole('button', { name: 'Cancelar inscripción en la sesión Apertura' }),
      ).toBeDisabled()
      expect(screen.getByText(/ya no se puede cancelar la inscripción/)).toBeInTheDocument()
    })

    it('disables the enrollment buttons while busy', () => {
      render(<SessionList sessions={[opening]} enrollment={enrollment()} busy />)
      expect(
        screen.getByRole('button', { name: 'Inscribirme en la sesión Apertura' }),
      ).toBeDisabled()
    })
  })
})
