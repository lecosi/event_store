import type { Event, EventStatus, User } from '../types'

/** Only admins manage users. The backend stays the real authority. */
export function isAdmin(user: User | null): boolean {
  return user?.role === 'admin'
}

/** Organizers and admins may create events. The backend stays the real authority. */
export function canCreateEvents(user: User | null): boolean {
  return user?.role === 'admin' || user?.role === 'organizer'
}

/** Admins manage any event; organizers only the ones they own. */
export function canManageEvent(user: User | null, event: Pick<Event, 'organizer_id'>): boolean {
  if (!user) return false
  return user.role === 'admin' || (user.role === 'organizer' && user.id === event.organizer_id)
}

const TRANSITIONS: Record<EventStatus, EventStatus[]> = {
  draft: ['published', 'cancelled'],
  published: ['finished', 'cancelled'],
  cancelled: [],
  finished: [],
}

/** The backend rejects edits to cancelled and finished events (409). */
export function isEditableStatus(status: EventStatus): boolean {
  return status !== 'cancelled' && status !== 'finished'
}

/** The backend rejects cancelling a registration of a finished event (409). */
export function canCancelRegistration(status: EventStatus): boolean {
  return status !== 'finished'
}

/** Status changes the backend accepts from the given status. */
export function nextStatuses(status: EventStatus): EventStatus[] {
  return TRANSITIONS[status]
}
