import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as speakersApi from '../api/speakers'
import type { Page, Speaker } from '../types'
import { SpeakerPicker } from './SpeakerPicker'

vi.mock('../api/speakers')

const speaker = (id: number, name: string): Speaker => ({ id, name, bio: '', email: null })
const pageOf = (...items: Speaker[]): Page<Speaker> => ({
  items,
  total: items.length,
  page: 1,
  size: 10,
  pages: 1,
})

const ada = speaker(1, 'Ada Lovelace')
const grace = speaker(2, 'Grace Hopper')

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(speakersApi.listSpeakers).mockResolvedValue(pageOf(ada, grace))
})

afterEach(() => {
  vi.useRealTimers()
})

const input = () => screen.getByLabelText('Ponente')

describe('SpeakerPicker', () => {
  it('lists the first speakers when the search box gets the focus', async () => {
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.focus(input())
    expect(await screen.findByRole('button', { name: 'Ada Lovelace' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Grace Hopper' })).toBeInTheDocument()
    expect(speakersApi.listSpeakers).toHaveBeenCalledWith({ q: undefined, size: 10 })
  })

  it('searches by the typed name', async () => {
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.change(input(), { target: { value: ' gra ' } })
    await waitFor(() =>
      expect(speakersApi.listSpeakers).toHaveBeenCalledWith({ q: 'gra', size: 10 }),
    )
  })

  it('waits for the user to stop typing before searching', async () => {
    vi.useFakeTimers()
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={300} />)
    fireEvent.change(input(), { target: { value: 'g' } })
    fireEvent.change(input(), { target: { value: 'gr' } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(299)
    })
    expect(speakersApi.listSpeakers).not.toHaveBeenCalled()
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1)
    })
    expect(speakersApi.listSpeakers).toHaveBeenCalledTimes(1)
    expect(speakersApi.listSpeakers).toHaveBeenCalledWith({ q: 'gr', size: 10 })
  })

  it('reports the chosen speaker and closes the results', async () => {
    const onSelect = vi.fn()
    render(<SpeakerPicker selected={null} onSelect={onSelect} delay={0} />)
    fireEvent.focus(input())
    fireEvent.click(await screen.findByRole('button', { name: 'Grace Hopper' }))
    expect(onSelect).toHaveBeenCalledWith({ id: 2, name: 'Grace Hopper' })
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
    expect(input()).toHaveValue('')
  })

  it('shows the selected speaker', () => {
    render(<SpeakerPicker selected={{ id: 9, name: 'Linus' }} onSelect={vi.fn()} />)
    expect(screen.getByText('Linus')).toBeInTheDocument()
  })

  it('shows a message when no speaker matches', async () => {
    vi.mocked(speakersApi.listSpeakers).mockResolvedValue(pageOf())
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.focus(input())
    expect(await screen.findByText('No se encontraron ponentes')).toBeInTheDocument()
  })

  it('shows an alert when the search fails', async () => {
    vi.mocked(speakersApi.listSpeakers).mockRejectedValue(new Error('boom'))
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.focus(input())
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudieron cargar los ponentes')
  })

  it('closes the results with Escape', async () => {
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.focus(input())
    await screen.findByRole('list')
    fireEvent.keyDown(input(), { key: 'Escape' })
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
  })

  it('shows the validation error under the search box', () => {
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} error="Elige un ponente" />)
    expect(screen.getByText('Elige un ponente')).toBeInTheDocument()
  })

  it('ignores the response of a search the user has already replaced', async () => {
    let resolveFirst: (page: Page<Speaker>) => void = () => {}
    vi.mocked(speakersApi.listSpeakers)
      .mockReturnValueOnce(new Promise((resolve) => (resolveFirst = resolve)))
      .mockResolvedValueOnce(pageOf(grace))
    render(<SpeakerPicker selected={null} onSelect={vi.fn()} delay={0} />)
    fireEvent.change(input(), { target: { value: 'a' } })
    await waitFor(() => expect(speakersApi.listSpeakers).toHaveBeenCalledTimes(1))
    fireEvent.change(input(), { target: { value: 'gr' } })
    expect(await screen.findByRole('button', { name: 'Grace Hopper' })).toBeInTheDocument()
    await act(async () => resolveFirst(pageOf(ada)))
    expect(screen.queryByRole('button', { name: 'Ada Lovelace' })).not.toBeInTheDocument()
  })
})
