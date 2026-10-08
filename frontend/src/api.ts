import type { components } from './generated/api'

export type Brief = components['schemas']['RecruitmentBrief']
export type Role = components['schemas']['Role']
export type ScenarioRequest = components['schemas']['ScenarioRequest']
export type Player = components['schemas']['PlayerStint']
export type Release = components['schemas']['DatasetRelease']
export type Team = components['schemas']['Team']
export type RoleSpec = components['schemas']['RoleSpecification']
export type Candidate = components['schemas']['Recommendation']
export type Results = components['schemas']['RecommendationResult']
export type Scenario = components['schemas']['ScenarioResult']
export type SquadSnapshot = Omit<components['schemas']['SquadSnapshot'], 'default_lineup'> & { default_lineup: Lineup }
export type SquadPlayer = components['schemas']['SquadPlayer']
export type Formation = components['schemas']['FormationDefinition']
export type Lineup = Omit<components['schemas']['LineupState'], 'bench'> & { bench: string[] }
export type Evaluation = Omit<components['schemas']['DashboardEvaluation'], 'lineup'> & { lineup: Lineup }
export type Rating = components['schemas']['PlayerRating']
export type Chemistry = components['schemas']['ChemistryResult']
export type CardPlayer = components['schemas']['PlayerCardData']
export type CataloguePage = components['schemas']['PlayerCataloguePage']
export type CatalogueMetadata = components['schemas']['PlayerCatalogueMetadata']
export type CatalogueDetail = components['schemas']['PlayerCatalogueDetail']

export const baseUrl = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '')

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(45000),
  })
  if (!response.ok) {
    const content = await response.json().catch(() => ({}))
    const detail = content.detail
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => item.msg).join('; ') : `Request failed (${response.status}). Please try again.`)
  }
  return response.json()
}

export function exportJson(name: string, value: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }))
  const link = document.createElement('a')
  link.href = url; link.download = name; link.click()
  URL.revokeObjectURL(url)
}
