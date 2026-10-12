import { useEffect, useState, type FormEvent } from 'react'
import { listUsers } from '../api/admin'
import { ErrorMessage } from '../components/ErrorMessage'
import { Pagination } from '../components/Pagination'
import { Spinner } from '../components/Spinner'
import { UserEditForm } from '../components/UserEditForm'
import { Button } from '../components/Button'
import { es, roleLabel } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/toastStore'
import type { Page, User } from '../types'
import { isAdmin } from '../utils/permissions'
import styles from './AdminUsersPage.module.css'
import pageStyles from './Pages.module.css'

const PAGE_SIZE = 10

/** What came back for one request; `page` and `query` say which request it answers. */
interface Outcome {
  page: number
  query: string
  data: Page<User> | null
  error: string | null
}

export default function AdminUsersPage() {
  const user = useAuthStore((s) => s.user)

  // After a reload the profile arrives later; do not flash "not allowed" before it does.
  if (!user) return <Spinner />
  if (!isAdmin(user)) return <ErrorMessage message={es.admin.notAllowed} />
  return <UserList admin={user} />
}

function UserList({ admin }: { admin: User }) {
  const loadMe = useAuthStore((s) => s.loadMe)
  const [text, setText] = useState('')
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)

  // The outcome is current only when it answers the search and page being shown.
  const current = outcome?.query === query && outcome.page === page ? outcome : null
  const items = current?.data?.items ?? []

  useEffect(() => {
    if (query === '') return
    let active = true
    listUsers({ email: query, page, size: PAGE_SIZE })
      .then((data) => active && setOutcome({ page, query, data, error: null }))
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : es.admin.loadFailed
        if (active) setOutcome({ page, query, data: null, error: message })
      })
    // A newer request makes this response stale: it must not overwrite the newer one.
    return () => {
      active = false
    }
  }, [query, page])

  function handleSearch(event: FormEvent) {
    event.preventDefault()
    setEditingId(null)
    setPage(1)
    setQuery(text.trim())
  }

  function changePage(next: number) {
    setEditingId(null)
    setPage(next)
  }

  function handleSaved(saved: User) {
    setOutcome((previous) =>
      previous?.data
        ? {
            ...previous,
            data: {
              ...previous.data,
              items: previous.data.items.map((item) => (item.id === saved.id ? saved : item)),
            },
          }
        : previous,
    )
    setEditingId(null)
    toast.success(es.admin.updated)
    // The navbar shows the logged-in user's name, so it has to be fetched again.
    if (saved.id === admin.id) void loadMe().catch(() => {})
  }

  return (
    <section>
      <div className={pageStyles.header}>
        <h1>{es.admin.title}</h1>
      </div>
      <form className={styles.search} role="search" onSubmit={handleSearch}>
        <input
          type="search"
          className={styles.searchInput}
          aria-label={es.admin.searchLabel}
          placeholder={es.admin.searchPlaceholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button type="submit">{es.admin.searchButton}</Button>
      </form>
      {query === '' && <p className={pageStyles.muted}>{es.admin.searchPrompt}</p>}
      {query !== '' && current === null && <Spinner />}
      <ErrorMessage message={current?.error} />
      {current?.data && items.length === 0 && (
        <p className={pageStyles.muted}>{es.admin.noResults(query)}</p>
      )}
      {items.length > 0 && (
        <ul className={`${pageStyles.panel} ${pageStyles.list}`}>
          {items.map((item) => (
            <li key={item.id} className={styles.row}>
              <div className={styles.summary}>
                <div className={styles.info}>
                  <strong className={styles.name}>{item.full_name}</strong>
                  <span className={pageStyles.muted}>{item.email}</span>
                  <span className={styles.badges}>
                    <span className={styles.badge}>{roleLabel(item.role)}</span>
                    <span className={item.is_active ? styles.active : styles.inactive}>
                      {item.is_active ? es.admin.active : es.admin.inactive}
                    </span>
                  </span>
                </div>
                <Button
                  variant="secondary"
                  aria-label={es.admin.editAria(item.full_name)}
                  disabled={editingId === item.id}
                  onClick={() => setEditingId(item.id)}
                >
                  {es.common.edit}
                </Button>
              </div>
              {editingId === item.id && (
                <UserEditForm
                  user={item}
                  isOwnAccount={item.id === admin.id}
                  onSaved={handleSaved}
                  onCancel={() => setEditingId(null)}
                />
              )}
            </li>
          ))}
        </ul>
      )}
      {/* Keeps the controls of the last loaded response while the next page is loading. */}
      {query !== '' && (
        <Pagination page={page} pages={outcome?.data?.pages ?? 0} onPageChange={changePage} />
      )}
    </section>
  )
}
