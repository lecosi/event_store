import { describe, expect, it } from 'vitest'
import { parseCapacity, validateEventForm, type EventFormValues } from './eventValidation'

const now = new Date('2030-01-01T12:00:00')

const valid: EventFormValues = {
  name: 'PyCon',
  description: 'Charlas',
  location: 'Medellín',
  start_at: '2030-02-01T09:00',
  end_at: '2030-02-01T18:00',
  capacity: '50',
}

const validate = (overrides: Partial<EventFormValues> = {}, requireFuture = true) =>
  validateEventForm({ ...valid, ...overrides }, { requireFuture, now })

describe('parseCapacity', () => {
  it.each([
    ['12', 12],
    [' 7 ', 7],
  ])('reads "%s" as %i', (text, expected) => {
    expect(parseCapacity(text)).toBe(expected)
  })

  it.each(['', 'abc', '1.5', '-3', '1e3'])('rejects "%s"', (text) => {
    expect(parseCapacity(text)).toBeNaN()
  })
})

describe('validateEventForm', () => {
  it('accepts a valid event', () => {
    expect(validate()).toEqual({})
  })

  it('requires a name', () => {
    expect(validate({ name: '   ' }).name).toBe('El nombre es obligatorio')
  })

  it('limits the name to 200 characters', () => {
    expect(validate({ name: 'a'.repeat(200) }).name).toBeUndefined()
    expect(validate({ name: 'a'.repeat(201) }).name).toBe(
      'El nombre debe tener como máximo 200 caracteres',
    )
  })

  it('requires a location', () => {
    expect(validate({ location: '' }).location).toBe('El lugar es obligatorio')
  })

  it('limits the location to 255 characters', () => {
    expect(validate({ location: 'a'.repeat(255) }).location).toBeUndefined()
    expect(validate({ location: 'a'.repeat(256) }).location).toBe(
      'El lugar debe tener como máximo 255 caracteres',
    )
  })

  it('limits the description to 5000 characters', () => {
    expect(validate({ description: 'a'.repeat(5000) }).description).toBeUndefined()
    expect(validate({ description: 'a'.repeat(5001) }).description).toBe(
      'La descripción debe tener como máximo 5000 caracteres',
    )
  })

  it('requires start and end dates', () => {
    const errors = validate({ start_at: '', end_at: '' })
    expect(errors.start_at).toBe('La fecha de inicio es obligatoria')
    expect(errors.end_at).toBe('La fecha de fin es obligatoria')
  })

  it('requires the end to be after the start', () => {
    expect(validate({ end_at: '2030-02-01T09:00' }).end_at).toBe(
      'El fin debe ser posterior al inicio',
    )
    expect(validate({ end_at: '2030-01-31T09:00' }).end_at).toBe(
      'El fin debe ser posterior al inicio',
    )
  })

  it('requires a future start when creating', () => {
    expect(validate({ start_at: '2029-12-31T09:00', end_at: '2030-02-01T09:00' }).start_at).toBe(
      'El inicio debe estar en el futuro',
    )
  })

  it('allows a past start when editing', () => {
    const errors = validate({ start_at: '2029-12-31T09:00', end_at: '2030-02-01T09:00' }, false)
    expect(errors.start_at).toBeUndefined()
  })

  it.each(['', '0', '-1', '2.5', 'abc'])('rejects the capacity "%s"', (capacity) => {
    expect(validate({ capacity }).capacity).toBe('La capacidad debe ser un número entero de al menos 1')
  })

  it('accepts a capacity of 1', () => {
    expect(validate({ capacity: '1' }).capacity).toBeUndefined()
  })

  it('uses the current time when none is given', () => {
    const errors = validateEventForm({ ...valid, start_at: '2000-01-01T09:00' }, { requireFuture: true })
    expect(errors.start_at).toBe('El inicio debe estar en el futuro')
  })
})
