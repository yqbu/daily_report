import { defineStore } from 'pinia'
import { callBridge, onBridgeJobFinished } from '../api/bridge'
import type { MaterialRow } from '../api/types'

export const useReportStore = defineStore('report', {
  state: () => ({
    materials: [] as MaterialRow[],
    materialTotal: 0,
    selectedTotal: 0,
    generating: false,
    generatedMarkdown: '',
    prompt: '',
    error: ''
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
      await onBridgeJobFinished((payload) => {
        this.generating = false
        if (!payload.ok) {
          this.error = payload.error || '生成失败'
          return
        }
        const result = payload.data as { result?: { report_markdown?: string; prompt_text?: string } }
        this.generatedMarkdown = result.result?.report_markdown || ''
        this.prompt = result.result?.prompt_text || this.prompt
      })
      await callBridge('generate_report', { date, save: true })
    }
  }
})
