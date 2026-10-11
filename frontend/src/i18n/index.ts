import type { EventStatus, Role } from '../types'
import { es } from './es'

export { es }

/** Shape every locale dictionary must have; derived from the Spanish one. */
export type Messages = typeof es

export const locales = { es } satisfies Record<string, Messages>

export type Locale = keyof typeof locales

export const DEFAULT_LOCALE: Locale = 'es'

/** Active dictionary. To add a language, add a file with the shape of `Messages` and register it in `locales`. */
export const messages: Messages = locales[DEFAULT_LOCALE]

/** Spanish label for an event status; unknown values are returned unchanged. */
export function statusLabel(status: EventStatus): string {
  return es.labels.status[status] ?? status
}

/** Spanish label for a user role; unknown values are returned unchanged. */
export function roleLabel(role: Role): string {
  return es.labels.role[role] ?? role
}
