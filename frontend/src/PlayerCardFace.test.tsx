import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import { PlayerCardFace, ratingTier } from './PlayerCardFace'

afterEach(cleanup)
describe('source-backed player cards', () => {
  it('keeps missing Physicality and OVR unavailable while showing five scored abilities', () => {
    render(<PlayerCardFace name="Cody Gakpo" position="ST" rating={null} scores={{
      Finishing: 38, 'Box Threat': 56, 'Link-Up / Creation': 80,
      'Carrying / 1v1': 82, Physicality: null, 'Defensive Activity': 58,
    }} caption="2025/26 · OBSERVED ST PROFILE"/>)
    expect(screen.getByLabelText('Six striker abilities for Cody Gakpo').children).toHaveLength(6)
    expect(screen.getByTitle('Physicality: unavailable. ST profile only.').textContent).toBe('—PHY')
    expect(screen.getByTitle('OVR unavailable: incomplete evidence or position model pending').textContent).toBe('—OVR')
    expect(screen.getByText('82')).toBeTruthy()
    expect(screen.queryByText('2025/26 · OBSERVED ST PROFILE')).toBeNull()
  })
  it('replaces a failed sourced portrait with an explicit shirt fallback', () => {
    render(<PlayerCardFace name="Example Player" position="CM" scores={{}}
      photo="https://cdn.pitchapi.dev/images/players/example.webp" caption="ROLE MODEL PENDING"/>)
    fireEvent.error(screen.getByAltText('Example Player'))
    expect(screen.queryByAltText('Example Player')).toBeNull()
    expect(screen.getByLabelText('Portrait unavailable for Example Player')).toBeTruthy()
    expect(screen.getByText('EP')).toBeTruthy()
  })
  it('marks scores pending during authoritative recalculation', () => {
    render(<PlayerCardFace name="Player" position="ST" rating={80} scores={{ Finishing: 90 }} pending caption="2025/26 · OBSERVED"/>)
    expect(screen.queryByText('90')).toBeNull()
    expect(screen.getByTitle('Recalculating').textContent).toBe('···OVR')
  })
})

it('uses the five rating finishes at their exact boundaries', () => {
  expect([49,50,69,70,79,80,89,90,110].map(ratingTier)).toEqual(['graphite','bronze','bronze','silver','silver','gold','gold','elite','elite'])
  expect(ratingTier(null)).toBe('unrated')
  render(<PlayerCardFace name="Player" position="ST" rating={110} country="France" club="Club" clubLogo="https://cdn.pitchapi.dev/images/teams/example.webp" scores={{Finishing:120}}/>)
  expect(screen.getByLabelText('France flag')).toBeTruthy()
  expect(screen.getByAltText('Club crest')).toBeTruthy()
  expect(screen.getByText('110')).toBeTruthy()
  expect(screen.getByText('120')).toBeTruthy()
})
