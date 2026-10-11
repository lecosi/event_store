import { describe, expect, it } from 'vitest'
import { validateConfirmation, validateEmail, validatePassword } from './validation'

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
