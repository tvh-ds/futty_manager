export type SavedState = { watchlist: string[]; notes: Record<string, string> }
export const emptySaved: SavedState = { watchlist: [], notes: {} }

export function validateSaved(value: unknown): SavedState {
  if (!value || typeof value !== 'object') throw new Error('The file is not a Scout watchlist export.')
  const record = value as Record<string, unknown>
  const candidate = 'saved' in record ? record.saved : record
  if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate))
    throw new Error('The file is not a Scout watchlist export.')
  const data = candidate as Record<string, unknown>
  if (!Array.isArray(data.watchlist) || data.watchlist.length > 300 ||
    data.watchlist.some(item => typeof item !== 'string' || !/^[A-Za-z0-9_-]{1,100}$/.test(item)))
    throw new Error('Watchlist contains invalid player identifiers.')
  if (!data.notes || typeof data.notes !== 'object' || Array.isArray(data.notes)) throw new Error('Notes are invalid.')
  const entries = Object.entries(data.notes)
  if (entries.length > 300 || entries.some(([key, note]) => !/^[A-Za-z0-9_-]{1,100}$/.test(key) ||
    ['__proto__', 'constructor', 'prototype'].includes(key) || typeof note !== 'string' || note.length > 5000))
    throw new Error('Notes exceed the supported format or size.')
  return { watchlist: [...new Set(data.watchlist as string[])], notes: Object.fromEntries(entries) }
}

export function loadSaved(): SavedState {
  const content = localStorage.getItem('scout.saved.v1')
  return content ? validateSaved(JSON.parse(content)) : emptySaved
}
