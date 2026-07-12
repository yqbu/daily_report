import type { AppProfileListPayload } from '../api/types'

interface CachedAppProfiles {
  savedAt: number
  payload: AppProfileListPayload
}

const CACHE_KEY = 'daily-report:app-profiles'
const CACHE_TTL_MS = 2 * 60 * 1000

export function useAppProfileCache() {
  function readAppProfileCache(): (CachedAppProfiles & { fresh: boolean }) | null {
    try {
      const raw = window.localStorage.getItem(CACHE_KEY)
      if (!raw) return null

      const cached = JSON.parse(raw) as CachedAppProfiles
      if (!cached?.payload || !Array.isArray(cached.payload.items)) return null

      return {
        ...cached,
        fresh: Date.now() - Number(cached.savedAt || 0) < CACHE_TTL_MS
      }
    } catch {
      clearAppProfileCache()
      return null
    }
  }

  function writeAppProfileCache(payload: AppProfileListPayload): void {
    window.localStorage.setItem(
      CACHE_KEY,
      JSON.stringify({
        savedAt: Date.now(),
        payload
      } satisfies CachedAppProfiles)
    )
  }

  function clearAppProfileCache(): void {
    window.localStorage.removeItem(CACHE_KEY)
  }

  return {
    readAppProfileCache,
    writeAppProfileCache,
    clearAppProfileCache
  }
}

