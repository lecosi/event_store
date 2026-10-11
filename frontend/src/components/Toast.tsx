import { es } from '../i18n'
import { useToastStore } from '../store/toastStore'
import styles from './Toast.module.css'

/** Renders the pending toasts; mounted once in Layout. */
export function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)
  return (
    <div className={styles.container} aria-live="polite">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`${styles.toast} ${styles[t.kind]}`}
          role={t.kind === 'error' ? 'alert' : 'status'}
        >
          <span>{t.message}</span>
          <button
            type="button"
            className={styles.close}
            aria-label={es.common.dismiss}
            onClick={() => dismiss(t.id)}
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
