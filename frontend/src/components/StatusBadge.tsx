import type { EventStatus } from '../types'
import { statusLabel } from '../i18n'
import styles from './StatusBadge.module.css'

export function StatusBadge({ status }: { status: EventStatus }) {
  return <span className={`${styles.badge} ${styles[status]}`}>{statusLabel(status)}</span>
}
