import { es } from '../i18n'
import type { FormErrors } from './eventValidation'
import { validateEmail } from './validation'

// Same limits as the backend SpeakerRequest schema; the backend stays the authority.
const NAME_MAX = 200
const BIO_MAX = 5000
const EMAIL_MAX = 255

export interface SpeakerFormValues {
  name: string
  bio: string
  email: string
}

export function validateSpeakerForm(values: SpeakerFormValues): FormErrors<SpeakerFormValues> {
  const errors: FormErrors<SpeakerFormValues> = {}
  const { validators } = es

  const name = values.name.trim()
  if (!name) errors.name = validators.nameRequired
  else if (name.length > NAME_MAX) errors.name = validators.nameMax(NAME_MAX)

  if (values.bio.length > BIO_MAX) errors.bio = validators.bioMax(BIO_MAX)

  // The email is optional: a blank one is not sent at all.
  const email = values.email.trim()
  if (email) {
    if (email.length > EMAIL_MAX) errors.email = validators.emailMax(EMAIL_MAX)
    else {
      const invalid = validateEmail(email)
      if (invalid) errors.email = invalid
    }
  }
  return errors
}
