import { useId, type SelectHTMLAttributes } from 'react'
import styles from './Input.module.css'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  error?: string | null
}

/** Labelled <select>, styled like Input. */
export function Select({ label, error, id, className, children, ...rest }: SelectProps) {
  const generatedId = useId()
  const selectId = id ?? generatedId
  const errorId = `${selectId}-error`
  return (
    <div className={styles.field}>
      <label htmlFor={selectId} className={styles.label}>
        {label}
      </label>
      <select
        {...rest}
        id={selectId}
        className={[styles.input, error ? styles.invalid : '', className].filter(Boolean).join(' ')}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
      >
        {children}
      </select>
      {error && (
        <p id={errorId} role="alert" className={styles.error}>
          {error}
        </p>
      )}
    </div>
  )
}
