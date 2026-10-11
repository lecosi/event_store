import type { User } from '../types'

/** Organizers and admins may create events. The backend stays the real authority. */
export function canCreateEvents(user: User | null): boolean {
  return user?.role === 'admin' || user?.role === 'organizer'
}
