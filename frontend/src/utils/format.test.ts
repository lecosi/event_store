process.env.TZ = 'UTC'

import { describe, expect, it } from 'vitest'
import { formatDateTime, fromInputValue, toInputValue } from './format'

describe('formatDateTime', () => {
  it('formats an ISO date with the es-CO day-first order', () => {
    const text = formatDateTime('2030-05-20T14:30:00Z')
    expect(text).toContain('20/05/2030')
    expect(text).toContain('2:30')
  })

  it('reads a date without offset as UTC', () => {
    expect(formatDateTime('2030-05-20T14:30:00')).toBe(formatDateTime('2030-05-20T14:30:00Z'))
  })
})

describe('toInputValue', () => {
  it('converts an ISO date to a datetime-local value without seconds', () => {
    expect(toInputValue('2030-05-20T09:05:00Z')).toBe('2030-05-20T09:05')
  })
})

describe('fromInputValue', () => {
  it('converts a datetime-local value to a UTC ISO string', () => {
    expect(fromInputValue('2030-05-20T09:05')).toBe('2030-05-20T09:05:00.000Z')
  })

  it('round trips with toInputValue', () => {
    expect(toInputValue(fromInputValue('2031-01-02T03:04'))).toBe('2031-01-02T03:04')
  })
})
