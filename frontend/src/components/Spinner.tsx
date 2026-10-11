import { es } from '../i18n'
import styles from './Spinner.module.css'

export function Spinner({ label = es.common.loading }: { label?: string }) {
  return <div className={styles.spinner} role="status" aria-label={label} />
}
