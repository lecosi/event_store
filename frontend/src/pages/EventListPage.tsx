import { useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ErrorMessage } from '../components/ErrorMessage'
import { EventCard } from '../components/EventCard'
import { Pagination } from '../components/Pagination'
import { SearchBar } from '../components/SearchBar'
import { Spinner } from '../components/Spinner'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { useEventStore } from '../store/eventStore'
import styles from './Pages.module.css'

const PAGE_SIZE = 9

export default function EventListPage() {
  // The URL (?q=...&page=...) is the source of truth: reload and back/forward just work.
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const requestedPage = Number(searchParams.get('page'))
  const page = Number.isInteger(requestedPage) && requestedPage >= 1 ? requestedPage : 1

  const token = useAuthStore((s) => s.token)
  const { items, pages, loading, error, fetchEvents } = useEventStore()

  // `token` is a dependency so the list is loaded again when the session starts or ends.
  useEffect(() => {
    void fetchEvents({ q: q || undefined, page, size: PAGE_SIZE })
  }, [q, page, token, fetchEvents])

  // A new search always goes back to the first page.
  const handleSearch = useCallback(
    (text: string) => setSearchParams(text ? { q: text } : {}),
    [setSearchParams],
  )

  const handlePageChange = (next: number) => {
    const params: Record<string, string> = { page: String(next) }
    if (q) params.q = q
    setSearchParams(params)
  }

  return (
    <section>
      <div className={styles.header}>
        <h1>{es.events.heading}</h1>
      </div>
      <SearchBar value={q} onSearch={handleSearch} />
      <ErrorMessage message={error} />
      {loading && <Spinner />}
      {!loading && !error && items.length === 0 && (
        <p className={styles.muted}>{q ? es.events.noMatch(q) : es.events.empty}</p>
      )}
      {!loading && items.length > 0 && (
        <div className={styles.grid}>
          {items.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      )}
      <Pagination page={page} pages={pages} onPageChange={handlePageChange} />
    </section>
  )
}
