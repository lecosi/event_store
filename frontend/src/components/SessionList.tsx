import { es } from '../i18n'
import type { EventStatus, Session } from '../types'
import { formatDateTime } from '../utils/format'
import { canCancelRegistration } from '../utils/permissions'
import { Button } from './Button'
import styles from './SessionList.module.css'

/** What the list needs to let the logged-in user enroll in sessions or cancel an enrollment. */
export interface SessionEnrollment {
  eventStatus: EventStatus
  isRegisteredToEvent: boolean
  onEnroll: (session: Session) => void
  onCancel: (session: Session) => void
}

interface SessionListProps {
  sessions: Session[]
  /** The edit and delete buttons are shown only when both handlers are given (managers). */
  onEdit?: (session: Session) => void
  onDelete?: (session: Session) => void
  /** The enroll and cancel buttons are shown only when given (logged-in users). */
  enrollment?: SessionEnrollment
  /** Disables the buttons while another action is running. */
  busy?: boolean
}

/** Why the user cannot enroll in (or cancel) the session right now; null when the button works. */
function blockedReason(session: Session, enrollment: SessionEnrollment): string | null {
  if (session.is_enrolled) {
    return canCancelRegistration(enrollment.eventStatus) ? null : es.sessions.cancelClosed
  }
  if (enrollment.eventStatus !== 'published') return es.sessions.eventNotPublished
  if (!enrollment.isRegisteredToEvent) return es.sessions.registerToEventFirst
  if (session.available_spots <= 0) return es.sessions.full
  return null
}

/** Sessions of an event ordered by start time. */
export function SessionList({
  sessions,
  onEdit,
  onDelete,
  enrollment,
  busy = false,
}: SessionListProps) {
  if (sessions.length === 0) return <p className={styles.empty}>{es.sessions.empty}</p>

  const ordered = [...sessions].sort((a, b) => a.start_at.localeCompare(b.start_at))
  return (
    <ul className={styles.list}>
      {ordered.map((session) => {
        const reason = enrollment ? blockedReason(session, enrollment) : null
        return (
          <li key={session.id} className={styles.item}>
            <div>
              <strong>{session.title}</strong> · {session.speaker.name}
              <div className={styles.meta}>
                {formatDateTime(session.start_at)} - {formatDateTime(session.end_at)} ·{' '}
                {es.sessions.spotsAvailable(session.available_spots, session.capacity)}
                {session.is_enrolled && ` · ${es.sessions.enrolled}`}
              </div>
              {reason && <div className={styles.meta}>{reason}</div>}
            </div>
            <div className={styles.actions}>
              {enrollment && !session.is_enrolled && (
                <Button
                  disabled={busy || reason !== null}
                  aria-label={es.sessions.enrollAria(session.title)}
                  onClick={() => enrollment.onEnroll(session)}
                >
                  {es.sessions.enroll}
                </Button>
              )}
              {enrollment && session.is_enrolled && (
                <Button
                  variant="secondary"
                  disabled={busy || reason !== null}
                  aria-label={es.sessions.cancelEnrollmentAria(session.title)}
                  onClick={() => enrollment.onCancel(session)}
                >
                  {es.sessions.cancelEnrollment}
                </Button>
              )}
              {onEdit && onDelete && (
                <>
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
                </>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
