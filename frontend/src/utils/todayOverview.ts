import type { AppProfileConfig } from '../api/types'

interface DonutSegment {
  value: number
  color: string
}

export function buildDonutBackground(items: DonutSegment[]): string {
  const total = items.reduce((sum, item) => sum + Math.max(0, item.value), 0)
  if (total <= 0) {
    return 'radial-gradient(circle at center, #fff 0 48%, transparent 49%), conic-gradient(#e6ebf3 0 100%)'
  }

  let cursor = 0
  const segments = items
    .filter((item) => item.value > 0)
    .map((item) => {
      const start = cursor
      cursor += (item.value / total) * 100
      return `${item.color} ${start.toFixed(2)}% ${cursor.toFixed(2)}%`
    })
    .join(', ')

  return `radial-gradient(circle at center, #fff 0 48%, transparent 49%), conic-gradient(${segments})`
}

export function iconSource(profile: AppProfileConfig): string {
  if (profile.icon_url) return profile.icon_url
  const icon = profile.icon_base64?.trim()
  if (!icon) return ''
  return icon.startsWith('data:') ? icon : `data:image/png;base64,${icon}`
}

