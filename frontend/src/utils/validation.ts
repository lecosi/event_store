import { es } from '../i18n'

// Mirrors the backend: a valid email address, passwords of at least 8 characters and a
// full name of 1 to 200 characters once trimmed.
export const MIN_PASSWORD_LENGTH = 8
export const FULL_NAME_MAX_LENGTH = 200
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/** Each validator returns an error message, or null when the value is valid. */
export function validateEmail(email: string): string | null {
  return EMAIL_PATTERN.test(email.trim()) ? null : es.validators.invalidEmail
}

export function validateFullName(fullName: string): string | null {
  const trimmed = fullName.trim()
  if (!trimmed) return es.validators.fullNameRequired
  if (trimmed.length > FULL_NAME_MAX_LENGTH) {
    return es.validators.fullNameMax(FULL_NAME_MAX_LENGTH)
  }
  return null
}

export function validatePassword(password: string): string | null {
  return password.length >= MIN_PASSWORD_LENGTH
    ? null
    : es.validators.passwordMin(MIN_PASSWORD_LENGTH)
}

export function validateConfirmation(password: string, confirmation: string): string | null {
  return password === confirmation ? null : es.validators.passwordMismatch
}
