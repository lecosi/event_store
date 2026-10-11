import { create } from 'zustand'
import { getEvent, listEvents } from '../api/events'
import { es } from '../i18n'
import type { Event, EventDetail, EventListParams } from '../types'

interface EventState {
  items: Event[]
  total: number
  page: number
  size: number
  pages: number
  loading: boolean
  error: string | null
  currentEvent: EventDetail | null
  detailLoading: boolean
  detailError: string | null
  /** Loads one page of events (optionally filtered) into the store. */
  fetchEvents: (params?: EventListParams) => Promise<void>
  /** Loads one event, with sessions and registration info, into `currentEvent`. */
  fetchEvent: (id: number) => Promise<void>
  clearCurrent: () => void
}

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

// Several requests can be in flight (typing in the search box, quick navigation):
// only the most recent one of each kind may write into the store.
let latestListRequest = 0
let latestDetailRequest = 0

export const useEventStore = create<EventState>((set) => ({
  items: [],
  total: 0,
  page: 1,
  size: 10,
  pages: 0,
  // True from the start so the list page never flashes its empty state before the first load.
  loading: true,
  error: null,
  currentEvent: null,
  detailLoading: false,
  detailError: null,

  fetchEvents: async (params = {}) => {
    const requestId = ++latestListRequest
    set({ loading: true, error: null })
    try {
      const result = await listEvents(params)
      if (requestId !== latestListRequest) return
      set({
        items: result.items,
        total: result.total,
        page: result.page,
        size: result.size,
        pages: result.pages,
        loading: false,
      })
    } catch (error) {
      if (requestId !== latestListRequest) return
      set({ loading: false, error: messageOf(error, es.events.loadListFailed) })
    }
  },

  fetchEvent: async (id) => {
    const requestId = ++latestDetailRequest
    set({ detailLoading: true, detailError: null })
    try {
      const event = await getEvent(id)
      if (requestId !== latestDetailRequest) return
      set({ currentEvent: event, detailLoading: false })
    } catch (error) {
      if (requestId !== latestDetailRequest) return
      set({
        currentEvent: null,
        detailLoading: false,
        detailError: messageOf(error, es.events.loadFailed),
      })
    }
  },

  clearCurrent: () => set({ currentEvent: null, detailError: null, detailLoading: false }),
}))
