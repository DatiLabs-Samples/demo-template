import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from './App'

describe('App', () => {
  it('renders the dashboard heading', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /dashboard/i })).toBeDefined()
  })

  it('renders the check backend button', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /check backend/i })).toBeDefined()
  })
})
