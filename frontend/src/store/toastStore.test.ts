import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { toast, useToastStore } from './toastStore'

beforeEach(() => {
  vi.useFakeTimers()
  useToastStore.setState({ toasts: [] })
})

afterEach(() => {
  vi.useRealTimers()
})

describe('toastStore', () => {
  it('queues success and error toasts in order with distinct ids', () => {
    toast.success('uno')
    toast.error('dos')
    const [first, second] = useToastStore.getState().toasts
    expect([first.kind, first.message]).toEqual(['success', 'uno'])
    expect([second.kind, second.message]).toEqual(['error', 'dos'])
    expect(first.id).not.toBe(second.id)
  })

  it('dismisses only the requested toast', () => {
    toast.success('uno')
    toast.success('dos')
    const [first] = useToastStore.getState().toasts
    useToastStore.getState().dismiss(first.id)
    expect(useToastStore.getState().toasts.map((t) => t.message)).toEqual(['dos'])
  })

  it('dismisses a toast automatically after four seconds', () => {
    toast.success('uno')
    vi.advanceTimersByTime(3999)
    expect(useToastStore.getState().toasts).toHaveLength(1)
    vi.advanceTimersByTime(1)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })
})
