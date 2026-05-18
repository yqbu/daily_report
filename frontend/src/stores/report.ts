import { defineStore } from 'pinia'
import { callBridge, onBridgeJobFinished } from '../api/bridge'
import type { MaterialRow } from '../api/types'

let jobListenerReady: Promise<unknown> | null = null

export const useReportStore = defineStore('report', {
  state: () => ({
    materials: [] as MaterialRow[],
    materialTotal: 0,
    selectedTotal: 0,
    generating: false,
    generatedMarkdown: '',
    prompt: '',
    error: '',
    activeJobId: ''
  }),
  actions: {
    async loadMaterials(date: string) {
      const data = await callBridge<{ items: MaterialRow[]; total: number; selected: number }>('get_materials', { date })
      this.materials = data.items
      this.materialTotal = data.total
      this.selectedTotal = data.selected
    },
    async updateSelected(key: string, selected: boolean) {
      await callBridge('update_material_selected', { key, selected })
      const item = this.materials.find((row) => row.key === key)
      if (item) item.selected = selected
      this.selectedTotal = this.materials.filter((row) => row.selected).length
    },
    async buildPrompt(date: string) {
      const data = await callBridge<{ prompt: string }>('build_report_prompt', { date })
      this.prompt = data.prompt
    },
    async generate(date: string) {
      this.generating = true
      this.error = ''
      jobListenerReady = jobListenerReady || onBridgeJobFinished((payload) => {
        const data = payload.data as { job_id?: string; result?: { report_markdown?: string; prompt_text?: string } } | undefined
        if (data?.job_id && this.activeJobId && data.job_id !== this.activeJobId) return
        this.generating = false
        if (!payload.ok) {
          this.error = payload.error || '生成失败'
          return
        }
        this.generatedMarkdown = data?.result?.report_markdown || ''
        this.prompt = data?.result?.prompt_text || this.prompt
        this.activeJobId = ''
      })
      try {
        await jobListenerReady
        const job = await callBridge<{ job_id?: string }>('generate_report', { date, save: true })
        this.activeJobId = job.job_id || ''
      } catch (error) {
        this.generating = false
        this.error = error instanceof Error ? error.message : String(error)
      }
    }
  }
})
