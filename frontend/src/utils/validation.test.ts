import { describe, expect, it } from 'vitest'
import {
  FULL_NAME_MAX_LENGTH,
  validateConfirmation,
  validateEmail,
  validateFullName,
  validatePassword,
} from './validation'

describe('validateEmail', () => {
  it.each(['ana@example.com', ' ana@example.com ', 'a.b+c@sub.example.co'])(
    'accepts "%s"',
    (email) => {
      expect(validateEmail(email)).toBeNull()
    },
  )

  it.each(['', 'ana', 'ana@', '@example.com', 'ana@example', 'ana @example.com'])(
    'rejects "%s"',
    (email) => {
      expect(validateEmail(email)).toBe('Ingresa un correo electrónico válido')
    },
  )
})

describe('validateFullName', () => {
  it('accepts a name and ignores surrounding spaces', () => {
    expect(validateFullName('  Ana Pérez  ')).toBeNull()
  })

  it.each(['', '   '])('rejects the blank name "%s"', (name) => {
    expect(validateFullName(name)).toBe('El nombre completo es obligatorio')
  })

  it('accepts a name of the maximum length', () => {
    expect(validateFullName('a'.repeat(FULL_NAME_MAX_LENGTH))).toBeNull()
  })

  it('counts the maximum length after trimming', () => {
    expect(validateFullName(` ${'a'.repeat(FULL_NAME_MAX_LENGTH)} `)).toBeNull()
  })

  it('rejects a name longer than the maximum', () => {
    expect(validateFullName('a'.repeat(FULL_NAME_MAX_LENGTH + 1))).toBe(
      'El nombre completo debe tener como máximo 200 caracteres',
    )
  })
})

describe('validatePassword', () => {
  it('accepts eight characters', () => {
    expect(validatePassword('12345678')).toBeNull()
  })

  it('rejects seven characters', () => {
    expect(validatePassword('1234567')).toBe('La contraseña debe tener al menos 8 caracteres')
  })
})

describe('validateConfirmation', () => {
  it('accepts matching passwords', () => {
    expect(validateConfirmation('secret123', 'secret123')).toBeNull()
  })

  it('rejects different passwords', () => {
    expect(validateConfirmation('secret123', 'secret124')).toBe('Las contraseñas no coinciden')
  })
})
