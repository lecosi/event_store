const HAS_OFFSET = /(Z|[+-]\d{2}:?\d{2})$/i

/** The backend treats datetimes without an offset as UTC, so the browser must too. */
function parseApiDate(iso: string): Date {
  return new Date(HAS_OFFSET.test(iso) ? iso : `${iso}Z`)
}

/** Fixed es-CO locale, e.g. "20 may 2030, 9:00 a. m.". */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeStyle: 'short' }).format(
    parseApiDate(iso),
  )
}

const pad = (n: number) => String(n).padStart(2, '0')

/** ISO string -> value for <input type="datetime-local"> (local time, no seconds). */
export function toInputValue(iso: string): string {
  const d = parseApiDate(iso)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** <input type="datetime-local"> value (local time) -> UTC ISO string for the API. */
export function fromInputValue(value: string): string {
  return new Date(value).toISOString()
}
