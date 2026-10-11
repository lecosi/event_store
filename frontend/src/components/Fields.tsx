import { useId, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
import styles from './Input.module.css'

interface FieldProps {
  label: string
  /** Validation message; when set the field is flagged as invalid. */
  error?: string | null
}

type SelectProps = FieldProps & SelectHTMLAttributes<HTMLSelectElement>
type TextAreaProps = FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>

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

/** Labelled <textarea>, styled like Input. */
export function TextArea({ label, error, id, className, ...rest }: TextAreaProps) {
  const generatedId = useId()
  const textAreaId = id ?? generatedId
  const errorId = `${textAreaId}-error`
  return (
    <div className={styles.field}>
      <label htmlFor={textAreaId} className={styles.label}>
        {label}
      </label>
      <textarea
        rows={4}
        {...rest}
        id={textAreaId}
        className={[styles.input, error ? styles.invalid : '', className].filter(Boolean).join(' ')}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
      />
      {error && (
        <p id={errorId} role="alert" className={styles.error}>
          {error}
        </p>
      )}
    </div>
  )
}
