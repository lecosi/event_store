import { useEffect, useState } from 'react'
import { es } from '../i18n'
import styles from './SearchBar.module.css'

interface SearchBarProps {
  /** Committed search text (for example the `q` URL param). */
  value: string
  /** Called once the user stops typing for `delay` ms. Pass a stable function. */
  onSearch: (text: string) => void
  delay?: number
}

export function SearchBar({ value, onSearch, delay = 300 }: SearchBarProps) {
  const [text, setText] = useState(value)
  const [syncedValue, setSyncedValue] = useState(value)

  // When the committed value changes from outside (back button), show it in the box.
  if (value !== syncedValue) {
    setSyncedValue(value)
    setText(value)
  }

  // Debounce: every keystroke restarts the timer, only the last one fires.
  useEffect(() => {
    if (text === value) return
    const timer = setTimeout(() => onSearch(text), delay)
    return () => clearTimeout(timer)
  }, [text, value, delay, onSearch])

  return (
    <input
      type="search"
      className={styles.input}
      aria-label={es.events.searchLabel}
      placeholder={es.events.searchPlaceholder}
      value={text}
      onChange={(e) => setText(e.target.value)}
    />
  )
}
