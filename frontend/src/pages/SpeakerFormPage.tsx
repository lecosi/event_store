import { useLocation, useNavigate } from 'react-router-dom'
import { createSpeaker } from '../api/speakers'
import { ErrorMessage } from '../components/ErrorMessage'
import { SpeakerForm } from '../components/SpeakerForm'
import { Spinner } from '../components/Spinner'
import { es } from '../i18n'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/toastStore'
import type { SpeakerPayload } from '../types'
import { canCreateEvents } from '../utils/permissions'

export default function SpeakerFormPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = useAuthStore((s) => s.user)

  // A rejection propagates to SpeakerForm, which shows the backend message.
  async function handleSubmit(payload: SpeakerPayload) {
    const speaker = await createSpeaker(payload)
    toast.success(es.speakers.created(speaker.name))
    // The first entry of the history has the key "default": there is no page to go back to.
    if (location.key === 'default') navigate('/')
    else navigate(-1)
  }

  // After a reload the profile arrives later; do not flash "not allowed" before it does.
  if (!user) return <Spinner />
  if (!canCreateEvents(user)) return <ErrorMessage message={es.speakers.notAllowed} />

  return (
    <section>
      <h1>{es.speakers.newTitle}</h1>
      <SpeakerForm onSubmit={handleSubmit} />
    </section>
  )
}
