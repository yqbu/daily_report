import { computed, onMounted, shallowRef } from 'vue'

import { callTypedBridge } from '../api/bridge'
import type { AppProfileConfig, OverviewPayload, TimelineEvent } from '../api/types'
import { datesBetween, startOfToday } from '../utils/date'

export type DateRange = [Date, Date]

export function useTodayOverviewData() {
  const dateRange = shallowRef<DateRange>([startOfToday(), startOfToday()])
  const overviewDays = shallowRef<OverviewPayload[]>([])
  const recentEvents = shallowRef<TimelineEvent[]>([])
  const appProfiles = shallowRef<AppProfileConfig[]>([])
  const loading = shallowRef(false)
  let loadRequestId = 0

  const selectedDates = computed(() => datesBetween(dateRange.value[0], dateRange.value[1]))

  async function loadOverview(): Promise<void> {
    const requestId = loadRequestId + 1
    loadRequestId = requestId
    loading.value = true

    try {
      const dates = selectedDates.value
      const [overviewPayloads, timelinePayloads, profilesPayload] = await Promise.all([
        Promise.all(dates.map((date) => callTypedBridge('getOverview', { date }))),
        Promise.all(
          dates.map((date) =>
            callTypedBridge('getTimeline', {
              date,
              filters: {
                sort_order: 'desc',
                limit: 8
              }
            })
          )
        ),
        callTypedBridge('listAppProfiles', {
          filters: {
            classification: 'all',
            keyword: '',
            track_enabled: null,
            sort_by: 'last_seen',
            sort_direction: 'desc'
          },
          page: 1,
          pageSize: 500,
          include_unobserved: true
        })
      ])

      if (requestId !== loadRequestId) return
      overviewDays.value = overviewPayloads
      recentEvents.value = timelinePayloads.flatMap((payload) => payload.items)
      appProfiles.value = profilesPayload.items
    } finally {
      if (requestId === loadRequestId) {
        loading.value = false
      }
    }
  }

  function handleDateRangeChange(value: DateRange | null): void {
    if (!value) {
      dateRange.value = [startOfToday(), startOfToday()]
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
