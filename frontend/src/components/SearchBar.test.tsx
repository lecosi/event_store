import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SearchBar } from './SearchBar'

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

const box = () => screen.getByRole('searchbox', { name: 'Buscar eventos' })

describe('SearchBar', () => {
  it('shows the committed value', () => {
    render(<SearchBar value="python" onSearch={() => {}} />)
    expect(box()).toHaveValue('python')
  })

  it('searches once, 300 ms after the last keystroke', () => {
    const onSearch = vi.fn()
    render(<SearchBar value="" onSearch={onSearch} />)
    fireEvent.change(box(), { target: { value: 'p' } })
    act(() => {
      vi.advanceTimersByTime(200)
    })
    fireEvent.change(box(), { target: { value: 'py' } })
    act(() => {
      vi.advanceTimersByTime(299)
    })
    expect(onSearch).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(onSearch).toHaveBeenCalledTimes(1)
    expect(onSearch).toHaveBeenCalledWith('py')
  })

  it('does not search when the text equals the committed value', () => {
    const onSearch = vi.fn()
    render(<SearchBar value="py" onSearch={onSearch} />)
    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(onSearch).not.toHaveBeenCalled()
  })

  it('follows the committed value when it changes from outside', () => {
    const { rerender } = render(<SearchBar value="py" onSearch={() => {}} />)
    rerender(<SearchBar value="" onSearch={() => {}} />)
    expect(box()).toHaveValue('')
  })
})
