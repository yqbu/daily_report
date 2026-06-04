import type {
  BuildPromptResponse,
  GenerateReportResponse,
  LatestReportResponse,
  OverviewDTO,
  PagedResult,
  SourceType,
  TimelineEvent
} from './types'

export function mockOverview(date = today()): OverviewDTO {
  return {
    date,
    collector_status: 'mock',
    active_time_sec: 12600,
    total_time_sec: 16800,
    active_time: '3h 30m',
    total_time: '4h 40m',
    app_session_count: 18,
    browser_count: 12,
    clipboard_count: 6,
    ai_prompt_count: 4,
    browser_event_count: 9,
    selected_material_count: 11,
    sensitive_count: 1,
    report_status: '未生成',
    top_apps: [
      { name: 'PyCharm', app_name: 'PyCharm', app_key: 'pycharm64.exe', seconds: 7200, session_count: 5, category: '开发编码' },
      { name: 'Edge', app_name: 'Edge', app_key: 'msedge.exe', seconds: 3200, session_count: 4, category: '资料调研' }
    ],
    source_distribution: [
      { source_type: 'app', count: 18 },
      { source_type: 'browser', count: 12 },
      { source_type: 'clipboard', count: 6 },
      { source_type: 'ai_prompt', count: 4 },
      { source_type: 'browser_event', count: 9 }
    ],
    category_distribution: [
      { category: '开发编码', count: 8 },
      { category: '资料调研', count: 5 },
      { category: 'AI 辅助', count: 4 }
    ],
    hourly_activity: Array.from({ length: 24 }, (_, hour) => ({
      hour,
      label: `${String(hour).padStart(2, '0')}:00`,
      active_sec: hour >= 9 && hour <= 18 ? 1200 : 0,
      total_sec: hour >= 9 && hour <= 18 ? 1600 : 0
    }))
  }
}

export function mockTimeline(date = today()): PagedResult<TimelineEvent> {
  const items: TimelineEvent[] = [
    {
      event_id: 'app:1',
      source_type: 'app',
      source_id: 1,
      start_time: `${date} 09:00:00`,
      end_time: `${date} 10:30:00`,
      title: 'PyCharm',
      subtitle: 'daily_report - API client',
      content_preview: 'daily_report - API client',
      category: '开发编码',
      is_selected: true,
      is_sensitive: false,
      is_deleted: false
    },
    {
      event_id: 'ai_prompt:1',
      source_type: 'ai_prompt',
      source_id: 1,
      start_time: `${date} 11:00:00`,
      end_time: null,
      title: 'AI 提问',
      subtitle: '本地 API 改造',
      content_preview: '如何设计 FastAPI sidecar API client',
      category: 'AI 辅助',
      is_selected: true,
      is_sensitive: false,
      is_deleted: false
    },
    {
      event_id: 'browser_event:1',
      source_type: 'browser_event',
      source_id: 1,
      start_time: `${date} 11:20:00`,
      end_time: null,
      title: '搜索: FastAPI sidecar API client',
      subtitle: 'google.com · 搜索',
      content_preview: 'FastAPI sidecar API client',
      category: '资料调研',
      is_selected: true,
      is_sensitive: false,
      is_deleted: false
    }
  ]
  return { items, total: items.length }
}

export function mockEntries(sourceType: SourceType, date = today()): PagedResult<Record<string, unknown>> {
  const items = mockTimeline(date).items
    .filter((item) => item.source_type === sourceType)
    .map((item) => ({ ...item }))
  return {
    items,
    total: items.length
  }
}

export function mockEntryDetail(sourceType: SourceType, id: number): Record<string, unknown> {
  return {
    source_type: sourceType,
    id,
    detail: {
      id,
      source_type: sourceType,
      title: 'Mock record',
      content_preview: 'Mock mode is enabled.'
    }
  }
}

export function mockBuildPrompt(date = today(), templateName = 'daily_standard'): BuildPromptResponse {
  return {
    date,
    template_name: templateName,
    prompt_text: `# ${date} 日报 Prompt\n\n当前为 mock 模式，启动 Python API 后可获取真实素材。`
  }
}

export function mockGenerateReport(date = today()): GenerateReportResponse {
  return {
    date,
    report_id: 0,
    report_markdown: `# ${date} 工作日报\n\n- Mock 模式日报内容。`,
    prompt_text: mockBuildPrompt(date).prompt_text
  }
}

export function mockLatestReport(date = today()): LatestReportResponse {
  return { date, report: null }
}

export function mockSettings(): Record<string, unknown> {
  return {
    collector: {},
    privacy: {},
    model: {},
    yasb: {},
    system: {}
  }
}

export function mockHealth(): Record<string, unknown> {
  return { status: 'ok', service: 'daily-report-api', version: 'mock' }
}

export function today(): string {
  return new Date().toISOString().slice(0, 10)
}
