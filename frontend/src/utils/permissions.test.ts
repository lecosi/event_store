import { describe, expect, it } from 'vitest'
import type { Role, User } from '../types'
import { canCreateEvents } from './permissions'

const userWith = (role: Role): User => ({ id: 1, email: 'a@b.co', role, is_active: true })

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
