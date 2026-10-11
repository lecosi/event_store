import { useEffect, useState } from 'react'
import { listSpeakers } from '../api/speakers'
import { es } from '../i18n'
import type { Speaker, SpeakerRef } from '../types'
import { Input } from './Input'
import styles from './SpeakerPicker.module.css'

interface SpeakerPickerProps {
  /** The chosen speaker; it does not have to be among the loaded results. */
  selected: SpeakerRef | null
  onSelect: (speaker: SpeakerRef) => void
  /** Validation message shown under the search box. */
  error?: string | null
  /** Milliseconds to wait after typing before asking the backend. */
  delay?: number
}

interface Outcome {
  query: string
  items: Speaker[]
  failed: boolean
}

const RESULTS_SIZE = 10

/** Search box that asks the backend for speakers by name and lets the user pick one. */
export function SpeakerPicker({ selected, onSelect, error, delay = 300 }: SpeakerPickerProps) {
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [outcome, setOutcome] = useState<Outcome | null>(null)

  const query = text.trim()

  // Each keystroke restarts the timer and drops the previous response, so only the latest search is shown.
  useEffect(() => {
    if (!open) return
    let current = true
    const timer = setTimeout(
      () => {
        listSpeakers({ q: query || undefined, size: RESULTS_SIZE })
          .then((page) => current && setOutcome({ query, items: page.items, failed: false }))
          .catch(() => current && setOutcome({ query, items: [], failed: true }))
      },
      query ? delay : 0,
    )
    return () => {
      current = false
      clearTimeout(timer)
    }
  }, [open, query, delay])

  // While the outcome belongs to another query the search is still running.
  const settled = open && outcome?.query === query ? outcome : null

  function choose(speaker: Speaker) {
    onSelect({ id: speaker.id, name: speaker.name })
    setText('')
    setOpen(false)
  }

  return (
    <div className={styles.picker}>
      <Input
        label={es.speakers.label}
        type="search"
        autoComplete="off"
        placeholder={es.speakers.searchPlaceholder}
        value={text}
        error={error}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setText(e.target.value)
          setOpen(true)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Escape') setOpen(false)
        }}
      />
      {selected && (
        <p className={styles.selected} aria-live="polite">
          {es.speakers.selected} <strong>{selected.name}</strong>
        </p>
      )}
      {open && (
        <div className={styles.results}>
          {settled === null && <p className={styles.note}>{es.speakers.searching}</p>}
          {settled?.failed && (
            <p role="alert" className={styles.note}>
              {es.speakers.loadFailed}
            </p>
          )}
          {settled && !settled.failed && settled.items.length === 0 && (
            <p className={styles.note}>{es.speakers.none}</p>
          )}
          {settled && settled.items.length > 0 && (
            <ul className={styles.list} aria-label={es.speakers.resultsLabel}>
              {settled.items.map((speaker) => (
                <li key={speaker.id}>
                  <button type="button" className={styles.option} onClick={() => choose(speaker)}>
                    {speaker.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
