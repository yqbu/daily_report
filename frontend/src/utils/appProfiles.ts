import type {
  AppProfileClassificationFilter,
  AppProfileConfig,
  AppProfileCounts,
  AppProfileListFilters,
  AppProfileListPayload
} from '../api/types'

export function emptyAppProfileList(): AppProfileListPayload {
  return {
    items: [],
    total: 0,
    page: 1,
    page_size: 500,
    counts: emptyCounts(),
    categories: []
  }
}

export function normalizeClassification(value?: string | null): AppProfileClassificationFilter {
  if (value === 'classified' || value === 'unclassified' || value === 'configured') return value
  return 'all'
}

export function filterProfiles(
  profiles: AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const keyword = filters.keyword?.trim().toLowerCase() ?? ''
  const category = filters.category?.trim() ?? ''
  const classification = normalizeClassification(filters.classification)

  return profiles.filter((profile) => {
    if (keyword && !profileMatchesKeyword(profile, keyword)) return false
    if (category && profile.category !== category) return false
    if (filters.track_enabled !== null && filters.track_enabled !== undefined) {
      if (profile.track_enabled !== filters.track_enabled) return false
    }
    if (classification === 'classified' && !profile.is_classified) return false
    if (classification === 'unclassified' && profile.is_classified) return false
    if (classification === 'configured' && !profile.is_configured) return false
    return true
  })
}

export function sortProfiles(
  profiles: AppProfileConfig[],
  filters: AppProfileListFilters
): AppProfileConfig[] {
  const direction = filters.sort_direction === 'asc' ? 1 : -1
  const sortBy = filters.sort_by ?? 'last_seen'

  return [...profiles].sort((left, right) => {
    let result = 0
    if (sortBy === 'name') {
      result = displayName(left).localeCompare(displayName(right), 'zh-CN')
    } else if (sortBy === 'duration') {
      result = Number(left.total_active_duration_sec || 0) - Number(right.total_active_duration_sec || 0)
    } else if (sortBy === 'session_count') {
      result = Number(left.session_count || 0) - Number(right.session_count || 0)
    } else {
      result = timestampValue(left.last_seen_at) - timestampValue(right.last_seen_at)
    }

    if (result === 0) {
      result = displayName(left).localeCompare(displayName(right), 'zh-CN')
    }
    return result * direction
  })
}

export function paginateProfiles(
  profiles: AppProfileConfig[],
  page: number,
  pageSize: number
): AppProfileConfig[] {
  const safePage = Math.max(1, Math.floor(page || 1))
  const safePageSize = Math.max(1, Math.floor(pageSize || 500))
  const start = (safePage - 1) * safePageSize
  return profiles.slice(start, start + safePageSize)
}

export function countProfiles(profiles: AppProfileConfig[]): AppProfileCounts {
  return profiles.reduce((counts, profile) => {
    counts.all += 1
    if (profile.is_classified) counts.classified += 1
    if (!profile.is_classified) counts.unclassified += 1
    if (profile.is_configured) counts.configured += 1
    if (!profile.track_enabled) counts.excluded += 1
    return counts
  }, emptyCounts())
}

function emptyCounts(): AppProfileCounts {
  return {
    all: 0,
    classified: 0,
    unclassified: 0,
    configured: 0,
    excluded: 0
  }
}

function profileMatchesKeyword(profile: AppProfileConfig, keyword: string): boolean {
  return [
    profile.app_key,
    profile.process_name,
    profile.exe_path,
    profile.default_display_name,
    profile.display_name,
    profile.effective_display_name,
    profile.sample_window_title
  ].some((value) => String(value || '').toLowerCase().includes(keyword))
}

function displayName(profile: AppProfileConfig): string {
  return profile.effective_display_name || profile.display_name || profile.default_display_name || profile.process_name
}

function timestampValue(value?: string | null): number {
  if (!value) return 0
  const timestamp = new Date(value).getTime()
  return Number.isFinite(timestamp) ? timestamp : 0
}

