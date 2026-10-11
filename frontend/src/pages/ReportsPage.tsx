import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { downloadParticipantsCsv, listParticipants } from '../api/reports'
import { Button } from '../components/Button'
import { ErrorMessage } from '../components/ErrorMessage'
import { Select } from '../components/Fields'
import { Input } from '../components/Input'
import { Pagination } from '../components/Pagination'
import { SearchBar } from '../components/SearchBar'
import { Spinner } from '../components/Spinner'
import { es, statusLabel } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/toastStore'
import type { EventStatus, Page, Participant, ParticipantFilters } from '../types'
import { canViewReports } from '../utils/permissions'
import styles from './ReportsPage.module.css'
import pageStyles from './Pages.module.css'

const PAGE_SIZE = 10
const STATUSES = Object.keys(es.labels.status) as EventStatus[]

/** What came back for one request; `key` says which filters and page it answers. */
interface Outcome {
  key: string
  data: Page<Participant> | null
  error: string | null
}

export default function ReportsPage() {
  const user = useAuthStore((s) => s.user)

  // After a reload the profile arrives later; do not flash "not allowed" before it does.
  if (!user) return <Spinner />
  if (!canViewReports(user)) return <ErrorMessage message={es.reports.notAllowed} />
  return <Report />
}

function Report() {
  // The URL is the source of truth: reload and back/forward just work.
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const rawStatus = searchParams.get('status') ?? ''
  const status = STATUSES.find((value) => value === rawStatus)
  const dateFrom = searchParams.get('date_from') ?? ''
  const dateTo = searchParams.get('date_to') ?? ''
  const eventId = Number(searchParams.get('event_id'))
  const requestedPage = Number(searchParams.get('page'))
  const page = Number.isInteger(requestedPage) && requestedPage >= 1 ? requestedPage : 1

  const filters = useMemo<ParticipantFilters>(
    () => ({
      q: q || undefined,
      status,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      event_id: Number.isInteger(eventId) && eventId > 0 ? eventId : undefined,
    }),
    [q, status, dateFrom, dateTo, eventId],
  )
  const invalidRange = dateFrom !== '' && dateTo !== '' && dateTo < dateFrom

  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [downloading, setDownloading] = useState(false)

  // The outcome is current only when it answers the filters and page being shown.
  const key = JSON.stringify([filters, page])
  const current = outcome?.key === key ? outcome : null
  const items = current?.data?.items ?? []

  useEffect(() => {
    if (invalidRange) return
    let active = true
    listParticipants({ ...filters, page, size: PAGE_SIZE })
      .then((data) => active && setOutcome({ key, data, error: null }))
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : es.reports.loadFailed
        if (active) setOutcome({ key, data: null, error: message })
      })
    // A newer request makes this response stale: it must not overwrite the newer one.
    return () => {
      active = false
    }
  }, [filters, page, key, invalidRange])

  /** Sets (or clears, when empty) one filter; changing a filter goes back to the first page. */
  const setFilter = useCallback(
    (name: string, value: string) =>
      setSearchParams((previous) => {
        const next = new URLSearchParams(previous)
        if (value) next.set(name, value)
        else next.delete(name)
        next.delete('page')
        return next
      }),
    [setSearchParams],
  )

  const handleSearch = useCallback((text: string) => setFilter('q', text), [setFilter])

  function changePage(next: number) {
    setSearchParams((previous) => {
      const params = new URLSearchParams(previous)
      params.set('page', String(next))
      return params
    })
  }

  async function handleDownload() {
    setDownloading(true)
    try {
      await downloadParticipantsCsv(filters)
      toast.success(es.reports.downloaded)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : es.reports.downloadFailed)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section>
      <div className={pageStyles.header}>
        <h1>{es.reports.title}</h1>
        <Button loading={downloading} disabled={invalidRange} onClick={() => void handleDownload()}>
          {es.reports.download}
        </Button>
      </div>

      <div className={pageStyles.panel}>
        <SearchBar value={q} onSearch={handleSearch} />
        <div className={styles.filters}>
          <Select
            label={es.reports.status}
            value={status ?? ''}
            onChange={(e) => setFilter('status', e.target.value)}
          >
            <option value="">{es.reports.allStatuses}</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {statusLabel(value)}
              </option>
            ))}
          </Select>
          <Input
            label={es.reports.dateFrom}
            type="date"
            value={dateFrom}
            onChange={(e) => setFilter('date_from', e.target.value)}
          />
          <Input
            label={es.reports.dateTo}
            type="date"
            value={dateTo}
            onChange={(e) => setFilter('date_to', e.target.value)}
          />
        </div>
        {filters.event_id !== undefined && (
          <p className={styles.eventFilter}>
            <span>{es.reports.eventFilter(filters.event_id)}</span>
            <Button variant="secondary" onClick={() => setFilter('event_id', '')}>
              {es.reports.clearEventFilter}
            </Button>
          </p>
        )}
      </div>

      <ErrorMessage message={invalidRange ? es.reports.invalidRange : current?.error} />
      {!invalidRange && current === null && <Spinner />}
      {current?.data && items.length === 0 && (
        <p className={pageStyles.muted}>{es.reports.empty}</p>
      )}
      {!invalidRange && items.length > 0 && (
        <div className={pageStyles.panel}>
          <table className={styles.table} aria-label={es.reports.tableLabel}>
            <thead>
              <tr>
                <th scope="col">{es.reports.fullName}</th>
                <th scope="col">{es.reports.email}</th>
                <th scope="col">{es.reports.event}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, index) => (
                <tr key={index}>
                  <td data-label={es.reports.fullName}>{item.full_name}</td>
                  <td data-label={es.reports.email}>{item.email}</td>
                  <td data-label={es.reports.event}>{item.event_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {/* Keeps the controls of the last loaded response while the next page is loading. */}
      {!invalidRange && (
        <Pagination page={page} pages={outcome?.data?.pages ?? 0} onPageChange={changePage} />
      )}
    </section>
  )
}
