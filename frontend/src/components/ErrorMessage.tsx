import styles from './ErrorMessage.module.css'

/** Banner for request-level errors (as opposed to per-field validation errors). */
export function ErrorMessage({ message }: { message: string | null | undefined }) {
  if (!message) return null
  return (
    <div role="alert" className={styles.alert}>
      {message}
    </div>
  )
}
