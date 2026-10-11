import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Pagination } from './Pagination'

describe('Pagination', () => {
  it('renders nothing when everything fits on one page', () => {
    render(<Pagination page={1} pages={1} onPageChange={() => {}} />)
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })

  it('shows the current page and total in a labelled navigation', () => {
    render(<Pagination page={2} pages={5} onPageChange={() => {}} />)
    expect(screen.getByRole('navigation', { name: 'Paginación' })).toBeInTheDocument()
    expect(screen.getByText('Página 2 de 5')).toBeInTheDocument()
  })

  it('goes to the previous and next pages', () => {
    const onPageChange = vi.fn()
    render(<Pagination page={2} pages={3} onPageChange={onPageChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Anterior' }))
    fireEvent.click(screen.getByRole('button', { name: 'Siguiente' }))
    expect(onPageChange.mock.calls).toEqual([[1], [3]])
  })

  it('disables previous on the first page', () => {
    render(<Pagination page={1} pages={3} onPageChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeEnabled()
  })

  it('disables next on the last page', () => {
    render(<Pagination page={3} pages={3} onPageChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Siguiente' })).toBeDisabled()
  })
})
