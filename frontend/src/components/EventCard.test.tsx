import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import type { Event } from '../types'
import { EventCard } from './EventCard'

const event: Event = {
  id: 12,
  name: 'PyCon Latam',
  description: '',
  location: 'Medellín',
  start_at: '2030-05-20T14:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 300,
  status: 'published',
  organizer_id: 1,
}

describe('EventCard', () => {
  it('links the name to the event detail', () => {
    render(
      <MemoryRouter>
        <EventCard event={event} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: 'PyCon Latam' })).toHaveAttribute('href', '/events/12')
  })

  it('shows status, place and capacity', () => {
    render(
      <MemoryRouter>
        <EventCard event={event} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Publicado')).toBeInTheDocument()
    expect(screen.getByText('Medellín')).toBeInTheDocument()
    expect(screen.getByText('300 cupos')).toBeInTheDocument()
  })
})
