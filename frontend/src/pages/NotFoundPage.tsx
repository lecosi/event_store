import { Link } from 'react-router-dom'
import { es } from '../i18n'

export default function NotFoundPage() {
  return (
    <section>
      <h1>{es.notFoundPage.title}</h1>
      <p>{es.notFoundPage.message}</p>
      <Link to="/">{es.notFoundPage.home}</Link>
    </section>
  )
}
