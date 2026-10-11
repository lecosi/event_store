import { es } from '../i18n'

// Same limits as the backend EventRequest schema; the backend stays the authority.
const NAME_MAX = 200
const LOCATION_MAX = 255
const DESCRIPTION_MAX = 5000

/** What the event form edits; dates are `datetime-local` values and capacity is raw text. */
export interface EventFormValues {
  name: string
  description: string
  location: string
  start_at: string
  end_at: string
  capacity: string
}

export type FormErrors<T> = Partial<Record<keyof T, string>>

/** Reads a whole number from an input text; NaN when it is not one. */
export function parseCapacity(value: string): number {
  return /^\d+$/.test(value.trim()) ? Number(value) : Number.NaN
}

interface Options {
  /** A new event must start in the future; an existing one may already have started. */
  requireFuture: boolean
  now?: Date
}

export function validateEventForm(
  values: EventFormValues,
  { requireFuture, now = new Date() }: Options,
): FormErrors<EventFormValues> {
  const errors: FormErrors<EventFormValues> = {}
  const { validators } = es

  if (!values.name.trim()) errors.name = validators.nameRequired
  else if (values.name.length > NAME_MAX) errors.name = validators.nameMax(NAME_MAX)

  if (!values.location.trim()) errors.location = validators.locationRequired
  else if (values.location.length > LOCATION_MAX) errors.location = validators.locationMax(LOCATION_MAX)

  if (values.description.length > DESCRIPTION_MAX)
    errors.description = validators.descriptionMax(DESCRIPTION_MAX)

  const start = new Date(values.start_at)
  const end = new Date(values.end_at)
  if (!values.start_at || Number.isNaN(start.getTime())) errors.start_at = validators.startRequired
  else if (requireFuture && start <= now) errors.start_at = validators.startFuture

  if (!values.end_at || Number.isNaN(end.getTime())) errors.end_at = validators.endRequired
  else if (!errors.start_at && end <= start) errors.end_at = validators.endAfterStart

  if (!(parseCapacity(values.capacity) >= 1)) errors.capacity = validators.capacityInvalid
  return errors
}
