import { describe, expect, it } from 'vitest'
import { validateSpeakerForm } from './speakerValidation'

const valid = { name: 'Grace Hopper', bio: '', email: '' }

describe('validateSpeakerForm', () => {
  it('accepts a name alone', () => {
    expect(validateSpeakerForm(valid)).toEqual({})
  })

  it('requires a name that is not only spaces', () => {
    expect(validateSpeakerForm({ ...valid, name: '   ' }).name).toBe('El nombre es obligatorio')
  })

  it('rejects a name longer than 200 characters', () => {
    expect(validateSpeakerForm({ ...valid, name: 'a'.repeat(201) }).name).toBe(
      'El nombre debe tener como máximo 200 caracteres',
    )
    expect(validateSpeakerForm({ ...valid, name: 'a'.repeat(200) }).name).toBeUndefined()
  })

  it('rejects a bio longer than 5000 characters', () => {
    expect(validateSpeakerForm({ ...valid, bio: 'a'.repeat(5001) }).bio).toBe(
      'La biografía debe tener como máximo 5000 caracteres',
    )
    expect(validateSpeakerForm({ ...valid, bio: 'a'.repeat(5000) }).bio).toBeUndefined()
  })

  it('accepts a valid email and ignores a blank one', () => {
    expect(validateSpeakerForm({ ...valid, email: 'grace@example.com' })).toEqual({})
    expect(validateSpeakerForm({ ...valid, email: '  ' })).toEqual({})
  })

  it('rejects a malformed email', () => {
    expect(validateSpeakerForm({ ...valid, email: 'grace' }).email).toBe(
      'Ingresa un correo electrónico válido',
    )
  })

  it('rejects an email longer than 255 characters', () => {
    const email = `${'a'.repeat(251)}@b.co`
    expect(validateSpeakerForm({ ...valid, email }).email).toBe(
      'El correo electrónico debe tener como máximo 255 caracteres',
    )
  })
})
