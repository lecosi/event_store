import type { EventStatus, Role } from '../types'
import { es } from './es'

export { es }

/** Spanish label for an event status; unknown values are returned unchanged. */
export function statusLabel(status: EventStatus): string {
  return es.labels.status[status] ?? status
}

/** Spanish label for a user role; unknown values are returned unchanged. */
export function roleLabel(role: Role): string {
  return es.labels.role[role] ?? role
}
