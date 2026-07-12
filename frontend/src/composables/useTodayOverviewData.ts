import { computed, onMounted, shallowRef } from 'vue'

import { callTypedDesktopApi } from '../api/desktop'
import type { AppProfileConfig, OverviewPayload, TimelineEvent } from '../api/types'
import { addDays, eachDateInRange, startOfToday } from '../utils/date'

type DateRange = [Date, Date]

export function useTodayOverviewData() {
  const today = startOfToday()
  const dateRange = shallowRef<DateRange>([today, today])
  const overviewDays = shallowRef<OverviewPayload[]>([])
  const recentEvents = shallowRef<TimelineEvent[]>([])
  const appProfiles = shallowRef<AppProfileConfig[]>([])
  const loading = shallowRef(false)
  let requestId = 0

  const selectedDates = computed(() => eachDateInRange(dateRange.value[0], dateRange.value[1]))

  async function loadOverview(): Promise<void> {
    const currentRequestId = requestId + 1
    requestId = currentRequestId
    loading.value = true

    try {
      const dates = selectedDates.value
      const [days, timeline, profiles] = await Promise.all([
        Promise.all(dates.map((date) => callTypedDesktopApi('getOverview', { date }))),
        callTypedDesktopApi('getTimeline', {
          startDate: dates[0],
          endDate: dates[dates.length - 1],
          filters: {},
          offset: 0,
          limit: 20,
          pageSize: 20
        }),
        callTypedDesktopApi('listAppProfiles', {
          filters: {},
          page: 1,
          pageSize: 500,
          include_unobserved: true,
          mode: 'saved',
          extract_if_empty: true,
          observed_scope: 'all'
        })
      ])

      if (currentRequestId !== requestId) return
      overviewDays.value = days
      recentEvents.value = timeline.items
      appProfiles.value = profiles.items
    } finally {
      if (currentRequestId === requestId) {
        loading.value = false
      }
    }
  }

  function handleDateRangeChange(value?: DateRange): void {
    if (value) {
      dateRange.value = normalizeRange(value)
    }
    void loadOverview()
  }

  onMounted(() => {
    void loadOverview()
  })

  return {
    dateRange,
    overviewDays,
    recentEvents,
    appProfiles,
    loading,
    selectedDates,
    loadOverview,
    handleDateRangeChange
  }
}

function normalizeRange(range: DateRange): DateRange {
  const [start, end] = range
  if (start <= end) return [start, end]
  return [end, start]
}
