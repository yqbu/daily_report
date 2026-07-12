import type {
  AppProfileClassificationFilter,
  AppProfileConfig,
  AppProfileCounts,
  AppProfileListFilters,
  AppProfileListPayload
} from '../api/types'

const appProfileCollator = new Intl.Collator('zh-CN', {
  numeric: true,
  sensitivity: 'base'
})

export function emptyAppProfileList(): AppProfileListPayload {
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 500,
    counts: emptyAppProfileCounts(),
    categories: []
  }
}

export function emptyAppProfileCounts(): AppProfileCounts {
  return {
    all: 0,
    classified: 0,
    unclassified: 0,
    configured: 0,
    excluded: 0
  }
}

export function filterProfiles(
  profiles: readonly AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const keyword = filters.keyword?.trim().toLocaleLowerCase() ?? ''
  const category = filters.category?.trim() ?? ''
  const classification = filters.classification ?? 'all'
  const trackEnabled = filters.track_enabled ?? null

  return profiles.filter((profile) => {
    if (keyword && !profileMatchesKeyword(profile, keyword)) return false
    if (category && profile.category !== category) return false
    if (classification === 'classified' && !profile.is_classified) return false
    if (classification === 'unclassified' && profile.is_classified) return false
    if (classification === 'configured' && !profile.is_configured) return false
    if (trackEnabled !== null && profile.track_enabled !== trackEnabled) return false
    return true
  })
}

export function sortProfiles(
  profiles: readonly AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const sortBy = filters.sort_by ?? 'last_seen'
  const sortDirection = filters.sort_direction ?? (sortBy === 'name' ? 'asc' : 'desc')
  const direction = sortDirection === 'asc' ? 1 : -1

  return [...profiles].sort((left, right) => {
    const primary = compareProfiles(left, right, sortBy)
    if (primary !== 0) return primary * direction
    return compareProfileNames(left, right) || appProfileCollator.compare(left.app_key, right.app_key)
  })
}

export function paginateProfiles(
  profiles: readonly AppProfileConfig[],
  page: number,
  pageSize: number
): AppProfileConfig[] {
  const safePage = Math.max(1, page)
  const safePageSize = Math.max(1, pageSize)
  const start = (safePage - 1) * safePageSize
  return profiles.slice(start, start + safePageSize)
}

export function countProfiles(profiles: readonly AppProfileConfig[]): AppProfileCounts {
  const counts = emptyAppProfileCounts()
  counts.all = profiles.length

  for (const profile of profiles) {
    if (profile.is_classified) {
      counts.classified += 1
    } else {
      counts.unclassified += 1
    }

    if (profile.is_configured) counts.configured += 1
    if (!profile.track_enabled) counts.excluded += 1
  }

  return counts
}

export function normalizeClassification(
  value: AppProfileClassificationFilter | undefined
): AppProfileClassificationFilter {
  return value ?? 'all'
}

function profileMatchesKeyword(profile: AppProfileConfig, keyword: string): boolean {
  const haystack = [
    profile.app_key,
    profile.process_name,
    profile.display_name,
    profile.effective_display_name,
    profile.default_display_name,
    profile.category
  ]
    .filter((value): value is string => typeof value === 'string' && value.length > 0)
    .join(' ')
    .toLocaleLowerCase()

  return haystack.includes(keyword)
}

function compareProfiles(
  left: AppProfileConfig,
  right: AppProfileConfig,
  sortBy: NonNullable<AppProfileListFilters['sort_by']>
): number {
  if (sortBy === 'name') {
    return compareProfileNames(left, right)
  }

  if (sortBy === 'duration') {
    return left.total_active_duration_sec - right.total_active_duration_sec
  }

  if (sortBy === 'session_count') {
    return left.session_count - right.session_count
  }

  return String(left.last_seen_at ?? '').localeCompare(String(right.last_seen_at ?? ''))
}

function compareProfileNames(left: AppProfileConfig, right: AppProfileConfig): number {
  return appProfileCollator.compare(profileDisplayName(left), profileDisplayName(right))
}

function profileDisplayName(profile: AppProfileConfig): string {
  return profile.effective_display_name || profile.display_name || profile.default_display_name || profile.process_name
}
