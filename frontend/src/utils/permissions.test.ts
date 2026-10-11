import { describe, expect, it } from 'vitest'
import type { EventStatus, Role, User } from '../types'
import {
  canCancelRegistration,
  canCreateEvents,
  canViewReports,
  canManageEvent,
  isAdmin,
  isEditableStatus,
  nextStatuses,
} from './permissions'

const userWith = (role: Role): User => ({
  id: 1,
  email: 'a@b.co',
  full_name: 'Ana Pérez',
  role,
  is_active: true,
})

describe('isAdmin', () => {
  it('allows an admin', () => {
    expect(isAdmin(userWith('admin'))).toBe(true)
  })

  it.each<Role>(['organizer', 'attendee'])('denies an %s', (role) => {
    expect(isAdmin(userWith(role))).toBe(false)
  })

  it('denies a visitor without a user', () => {
    expect(isAdmin(null)).toBe(false)
  })
})

describe('canCreateEvents', () => {
  it.each<Role>(['admin', 'organizer'])('allows an %s', (role) => {
    expect(canCreateEvents(userWith(role))).toBe(true)
  })

  it('denies an attendee', () => {
    expect(canCreateEvents(userWith('attendee'))).toBe(false)
  })

  it('denies a visitor without a user', () => {
    expect(canCreateEvents(null)).toBe(false)
  })
})

describe('canManageEvent', () => {
  const event = { organizer_id: 1 }
  const userWithId = (role: Role, id: number): User => ({
    id,
    email: 'a@b.co',
    full_name: 'Ana Pérez',
    role,
    is_active: true,
  })

  it('allows an admin on any event', () => {
    expect(canManageEvent(userWithId('admin', 99), event)).toBe(true)
  })

  it('allows the organizer who owns the event', () => {
    expect(canManageEvent(userWithId('organizer', 1), event)).toBe(true)
  })

  it('denies an organizer who does not own the event', () => {
    expect(canManageEvent(userWithId('organizer', 2), event)).toBe(false)
  })

  it('denies an attendee even when the ids match', () => {
    expect(canManageEvent(userWithId('attendee', 1), event)).toBe(false)
  })

  it('denies a visitor without a user', () => {
    expect(canManageEvent(null, event)).toBe(false)
  })
})

describe('nextStatuses', () => {
  it('lets a draft be published or cancelled', () => {
    expect(nextStatuses('draft')).toEqual(['published', 'cancelled'])
  })

  it('lets a published event be finished or cancelled', () => {
    expect(nextStatuses('published')).toEqual(['finished', 'cancelled'])
  })

  it.each<EventStatus>(['cancelled', 'finished'])('offers nothing from %s', (status) => {
    expect(nextStatuses(status)).toEqual([])
  })
})

describe('isEditableStatus', () => {
  it.each<EventStatus>(['draft', 'published'])('allows editing a %s event', (status) => {
    expect(isEditableStatus(status)).toBe(true)
  })

  it.each<EventStatus>(['cancelled', 'finished'])('denies editing a %s event', (status) => {
    expect(isEditableStatus(status)).toBe(false)
  })
})

describe('canCancelRegistration', () => {
  it.each<EventStatus>(['draft', 'published', 'cancelled'])(
    'allows cancelling a registration of a %s event',
    (status) => {
      expect(canCancelRegistration(status)).toBe(true)
    },
  )

  it('denies cancelling a registration of a finished event', () => {
    expect(canCancelRegistration('finished')).toBe(false)
  })
})

describe('canViewReports', () => {
  it.each<Role>(['admin', 'organizer'])('allows an %s', (role) => {
    expect(canViewReports(userWith(role))).toBe(true)
  })

  it('denies an attendee', () => {
    expect(canViewReports(userWith('attendee'))).toBe(false)
  })

  it('denies a visitor without a user', () => {
    expect(canViewReports(null)).toBe(false)
  })
})
