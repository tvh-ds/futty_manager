import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'
import Players from './Players'

vi.mock('./api', () => ({ api: vi.fn(async (path: string) => path === '/catalogue' ? {
  catalogue_id: 'test', total: 0, leagues: ['England', 'Spain'],
  teams: { England: ['Liverpool FC'], Spain: ['Barcelona'] }, positions: ['ST', 'GK'],
  squad_mappings: {}, limitations: [],
} : { catalogue_id: 'test', total: 0, offset: 0, limit: 24, items: [] }) }))
afterEach(cleanup)
function Location() { return <output data-testid="filters">{useLocation().search}</output> }

it('preserves combined filters when controls change before the router renders', async () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><Players/><Location/></MemoryRouter></QueryClientProvider>)
  await waitFor(() => expect(screen.getByRole('option', { name: 'England' })).toBeTruthy())
  act(() => {
    fireEvent.change(screen.getByRole('combobox', { name: 'League' }), { target: { value: 'England' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Team · 2025/26' }), { target: { value: 'Liverpool FC' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Position' }), { target: { value: 'ST' } })
  })
  const params = new URLSearchParams(screen.getByTestId('filters').textContent || '')
  expect(params.get('league')).toBe('England')
  expect(params.get('team')).toBe('Liverpool FC')
  expect(params.get('position')).toBe('ST')
  fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
  expect(screen.getByTestId('filters').textContent).toBe('')
})
