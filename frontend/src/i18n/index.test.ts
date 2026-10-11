import { describe, expect, it } from 'vitest'
import type { EventStatus, Role } from '../types'
import { DEFAULT_LOCALE, es, locales, messages, roleLabel, statusLabel } from '.'

describe('i18n labels', () => {
  it('translates an event status to Spanish', () => {
    expect(statusLabel('published')).toBe('Publicado')
  })

  it('returns an unknown event status unchanged', () => {
    expect(statusLabel('archived' as EventStatus)).toBe('archived')
  })

  it('translates a role to Spanish', () => {
    expect(roleLabel('organizer')).toBe('Organizador')
  })

  it('returns an unknown role unchanged', () => {
    expect(roleLabel('guest' as Role)).toBe('guest')
  })
})

describe('i18n locales', () => {
  it('selects the default locale as the active messages', () => {
    expect(messages).toBe(locales[DEFAULT_LOCALE])
  })

  it('registers the Spanish dictionary under the es locale', () => {
    expect(locales.es).toBe(es)
  })
})
