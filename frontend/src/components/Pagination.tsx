import { es } from '../i18n'
import { Button } from './Button'
import styles from './Pagination.module.css'

interface PaginationProps {
  page: number
  pages: number
  onPageChange: (page: number) => void
}

/** Previous/next controls; hidden when everything fits on one page. */
export function Pagination({ page, pages, onPageChange }: PaginationProps) {
  if (pages <= 1) return null
  return (
    <nav className={styles.pagination} aria-label={es.common.paginationLabel}>
      <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        {es.common.previous}
      </Button>
      <span aria-live="polite">{es.common.page(page, pages)}</span>
      <Button variant="secondary" disabled={page >= pages} onClick={() => onPageChange(page + 1)}>
        {es.common.next}
      </Button>
    </nav>
  )
}
