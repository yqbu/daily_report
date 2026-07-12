export function formatDuration(seconds: number): string {
  const safeSeconds = Math.max(0, Math.round(Number(seconds) || 0))
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  if (hours > 0 && minutes > 0) return `${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h`
  return `${minutes}m`
}

export function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

export function getPercent(value: number, total: number): number {
  const safeTotal = Number(total) || 0
  if (safeTotal <= 0) return 0
  return (Math.max(0, Number(value) || 0) / safeTotal) * 100
}

