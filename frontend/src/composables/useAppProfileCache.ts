import type { AppProfileListPayload } from '../api/types'

let appProfileCache: AppProfileListPayload | null = null
let appProfileCacheUpdatedAt = 0
const APP_PROFILE_CACHE_TTL_MS = 60_000

export function useAppProfileCache() {
  function readAppProfileCache(): { payload: AppProfileListPayload; fresh: boolean } | null {
    if (!appProfileCache) return null

    return {
      payload: appProfileCache,
      fresh: Date.now() - appProfileCacheUpdatedAt < APP_PROFILE_CACHE_TTL_MS
    }
  }

  function writeAppProfileCache(payload: AppProfileListPayload): void {
    appProfileCache = payload
    appProfileCacheUpdatedAt = Date.now()
  }

  function clearAppProfileCache(): void {
    appProfileCache = null
    appProfileCacheUpdatedAt = 0
  }

  return {
    readAppProfileCache,
    writeAppProfileCache,
    clearAppProfileCache
  }
}
