export function formatDuration(seconds: number): string {
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

export function formatTime(value: string): string {
  const match = value.match(/T?(\d{2}):(\d{2})(?::\d{2})?/)
  if (match) return `${match[1]}:${match[2]}`
  return value || '--:--'
}

export function getPercent(value: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((value / total) * 1000) / 10
}
