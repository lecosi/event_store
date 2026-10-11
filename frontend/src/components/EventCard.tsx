import { Link } from 'react-router-dom'
import { es } from '../i18n'
import type { Event } from '../types'
import { formatDateTime } from '../utils/format'
import { StatusBadge } from './StatusBadge'
import styles from './EventCard.module.css'

export function EventCard({ event }: { event: Event }) {
  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <h2 className={styles.title}>
          <Link to={`/events/${event.id}`}>{event.name}</Link>
        </h2>
        <StatusBadge status={event.status} />
      </div>
      <p className={styles.meta}>{formatDateTime(event.start_at)}</p>
      <p className={styles.meta}>{event.location}</p>
      <p className={styles.meta}>{es.events.spots(event.capacity)}</p>
    </article>
  )
}
