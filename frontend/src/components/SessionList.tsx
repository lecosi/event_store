import { es } from '../i18n'
import type { Session } from '../types'
import { formatDateTime } from '../utils/format'
import { Button } from './Button'
import styles from './SessionList.module.css'

interface SessionListProps {
  sessions: Session[]
  /** The edit and delete buttons are shown only when both handlers are given (managers). */
  onEdit?: (session: Session) => void
  onDelete?: (session: Session) => void
  /** Disables the buttons while another action is running. */
  busy?: boolean
}

/** Sessions of an event ordered by start time. */
export function SessionList({ sessions, onEdit, onDelete, busy = false }: SessionListProps) {
  if (sessions.length === 0) return <p className={styles.empty}>{es.sessions.empty}</p>

  const ordered = [...sessions].sort((a, b) => a.start_at.localeCompare(b.start_at))
  return (
    <ul className={styles.list}>
      {ordered.map((session) => (
        <li key={session.id} className={styles.item}>
          <div>
            <strong>{session.title}</strong> · {session.speaker.name}
            <div className={styles.meta}>
              {formatDateTime(session.start_at)} - {formatDateTime(session.end_at)} ·{' '}
              {es.sessions.seats(session.capacity)}
            </div>
          </div>
          {onEdit && onDelete && (
            <div className={styles.actions}>
              <Button
                variant="secondary"
                disabled={busy}
                aria-label={es.sessions.editAria(session.title)}
                onClick={() => onEdit(session)}
              >
                {es.common.edit}
              </Button>
              <Button
                variant="danger"
                disabled={busy}
                aria-label={es.sessions.deleteAria(session.title)}
                onClick={() => onDelete(session)}
              >
                {es.common.delete}
              </Button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
