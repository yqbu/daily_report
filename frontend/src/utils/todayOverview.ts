import type { AppProfileConfig } from '../api/types'

export interface DonutSegment {
  value: number
  percent: number
  color: string
}

export function iconSource(profile: AppProfileConfig): string {
  if (profile.icon_url) return profile.icon_url

  const icon = profile.icon_base64?.trim()
  if (!icon) return ''
  return icon.startsWith('data:') ? icon : `data:image/png;base64,${icon}`
}

export function buildDonutBackground(items: DonutSegment[]): string {
  let cursor = 0
  const segments = items
    .filter((item) => item.value > 0)
    .map((item) => {
      const start = cursor
      const end = Math.min(100, cursor + item.percent)
      cursor = end
      return `${item.color} ${start}% ${end}%`
    })

  if (segments.length === 0) {
    segments.push('#edf1f7 0% 100%')
  } else if (cursor < 100) {
    segments.push(`#edf1f7 ${cursor}% 100%`)
  }

  return `radial-gradient(circle at center, #fff 0 48%, transparent 49%), conic-gradient(${segments.join(', ')})`
}
