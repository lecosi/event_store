import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as eventsApi from '../api/events'
import { ApiError } from '../api/client'
import { es } from '../i18n'
import type { Event, EventDetail, Page } from '../types'
import { useEventStore } from './eventStore'

vi.mock('../api/events')

const event = (id: number): Event => ({
  id,
  name: `Evento ${id}`,
  description: '',
  location: 'Bogotá',
  start_at: '2030-05-20T09:00:00Z',
  end_at: '2030-05-21T18:00:00Z',
  capacity: 10,
  status: 'published',
  organizer_id: 1,
})

const detail = (id: number): EventDetail => ({
  ...event(id),
  sessions: [],
  registered_count: 0,
  available_spots: 10,
  is_registered: false,
})

const pageOf = (items: Event[], overrides: Partial<Page<Event>> = {}): Page<Event> => ({
  items,
  total: items.length,
  page: 1,
  size: 9,
  pages: 1,
  ...overrides,
})

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((r) => {
    resolve = r
  })
  return { promise, resolve }
}

const initial = useEventStore.getState()

beforeEach(() => {
  vi.resetAllMocks()
  useEventStore.setState(initial, true)
})

describe('eventStore list', () => {
  it('starts in the loading state so the first render never shows an empty list', () => {
    expect(useEventStore.getState().loading).toBe(true)
  })

  it('stores the page returned by the api', async () => {
    vi.mocked(eventsApi.listEvents).mockResolvedValue(
      pageOf([event(1), event(2)], { total: 15, page: 2, pages: 2 }),
    )
    await useEventStore.getState().fetchEvents({ page: 2, size: 9 })
    const state = useEventStore.getState()
    expect(eventsApi.listEvents).toHaveBeenCalledWith({ page: 2, size: 9 })
    expect(state.items.map((e) => e.id)).toEqual([1, 2])
    expect([state.total, state.page, state.pages]).toEqual([15, 2, 2])
    expect(state.loading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('exposes the loading flag while the request is in flight', async () => {
    const pending = deferred<Page<Event>>()
    vi.mocked(eventsApi.listEvents).mockReturnValue(pending.promise)
    const request = useEventStore.getState().fetchEvents()
    expect(useEventStore.getState().loading).toBe(true)
    pending.resolve(pageOf([]))
    await request
    expect(useEventStore.getState().loading).toBe(false)
  })

  it('keeps the api error message', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue(new ApiError('Sin conexión', null))
    await useEventStore.getState().fetchEvents()
    expect(useEventStore.getState().error).toBe('Sin conexión')
    expect(useEventStore.getState().loading).toBe(false)
  })

  it('falls back to a Spanish message for non-error rejections', async () => {
    vi.mocked(eventsApi.listEvents).mockRejectedValue('boom')
    await useEventStore.getState().fetchEvents()
    expect(useEventStore.getState().error).toBe(es.events.loadListFailed)
  })

  it('lets only the latest request write its result', async () => {
    const first = deferred<Page<Event>>()
    const second = deferred<Page<Event>>()
    vi.mocked(eventsApi.listEvents)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise)
    const slow = useEventStore.getState().fetchEvents({ q: 'a' })
    const fast = useEventStore.getState().fetchEvents({ q: 'ab' })
    second.resolve(pageOf([event(2)]))
    await fast
    first.resolve(pageOf([event(1)]))
    await slow
    expect(useEventStore.getState().items.map((e) => e.id)).toEqual([2])
  })

  it('ignores the failure of a request that is no longer the latest', async () => {
    const first = deferred<Page<Event>>()
    vi.mocked(eventsApi.listEvents)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(pageOf([event(2)]))
    const slow = useEventStore.getState().fetchEvents({ q: 'a' })
    await useEventStore.getState().fetchEvents({ q: 'ab' })
    first.resolve(Promise.reject(new ApiError('tarde', 500)) as never)
    await slow
    expect(useEventStore.getState().error).toBeNull()
  })
})

describe('eventStore detail', () => {
  it('stores the fetched event', async () => {
    vi.mocked(eventsApi.getEvent).mockResolvedValue(detail(5))
    await useEventStore.getState().fetchEvent(5)
    const state = useEventStore.getState()
    expect(eventsApi.getEvent).toHaveBeenCalledWith(5)
    expect(state.currentEvent?.id).toBe(5)
    expect(state.detailLoading).toBe(false)
    expect(state.detailError).toBeNull()
  })

  it('clears the event and keeps the message when the fetch fails', async () => {
    useEventStore.setState({ currentEvent: detail(5) })
    vi.mocked(eventsApi.getEvent).mockRejectedValue(new ApiError('Evento no encontrado.', 404))
    await useEventStore.getState().fetchEvent(5)
    const state = useEventStore.getState()
    expect(state.currentEvent).toBeNull()
    expect(state.detailError).toBe('Evento no encontrado.')
  })

  it('falls back to a Spanish message for non-error rejections', async () => {
    vi.mocked(eventsApi.getEvent).mockRejectedValue('boom')
    await useEventStore.getState().fetchEvent(5)
    expect(useEventStore.getState().detailError).toBe(es.events.loadFailed)
  })

  it('ignores an older detail response that arrives after a newer one', async () => {
    const first = deferred<EventDetail>()
    vi.mocked(eventsApi.getEvent)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce(detail(6))
    const slow = useEventStore.getState().fetchEvent(5)
    await useEventStore.getState().fetchEvent(6)
    first.resolve(detail(5))
    await slow
    expect(useEventStore.getState().currentEvent?.id).toBe(6)
  })

  it('clearCurrent resets the detail state', () => {
    useEventStore.setState({ currentEvent: detail(5), detailError: 'x', detailLoading: true })
    useEventStore.getState().clearCurrent()
    const state = useEventStore.getState()
    expect([state.currentEvent, state.detailError, state.detailLoading]).toEqual([null, null, false])
  })
})
