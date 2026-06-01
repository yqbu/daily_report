import { defineStore } from 'pinia'
import { buildPrompt, generateReport, getLatestReport } from '../api/reports'

export const useReportsStore = defineStore('reports', {
  state: () => ({
    promptText: '',
    reportMarkdown: '',
    latestReport: null as Record<string, unknown> | null,
    loadingPrompt: false,
    generating: false,
    error: null as string | null
  }),
  actions: {
    async buildPrompt(date?: string, templateName = 'daily_standard') {
      this.loadingPrompt = true
      this.error = null
      try {
        const result = await buildPrompt({ date, template_name: templateName })
        this.promptText = result.prompt_text
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loadingPrompt = false
      }
    },
    async generateReport(date?: string, templateName = 'daily_standard') {
      this.generating = true
      this.error = null
      try {
        const result = await generateReport({ date, template_name: templateName, save: true })
        this.reportMarkdown = result.report_markdown
        this.promptText = result.prompt_text || this.promptText
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
        throw error
      } finally {
        this.generating = false
      }
    },
    async loadLatestReport(date?: string) {
      const result = await getLatestReport(date)
      this.latestReport = result.report
      this.reportMarkdown = result.report?.report_markdown || ''
    }
  }
})

