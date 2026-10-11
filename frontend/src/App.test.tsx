import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('shows the application name', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'Mis Eventos' })).toBeInTheDocument()
  })
})
