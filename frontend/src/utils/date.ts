export function startOfToday(): Date {
  const date = new Date()
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

export function addDays(date: Date, offset: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + offset)
  return next
}

export function datesBetween(start: Date, end: Date): string[] {
  const normalizedStart = start <= end ? start : end
  const normalizedEnd = start <= end ? end : start
  const dates: string[] = []
  let cursor = new Date(normalizedStart.getFullYear(), normalizedStart.getMonth(), normalizedStart.getDate())

  while (cursor <= normalizedEnd) {
    dates.push(formatIsoDate(cursor))
    cursor = addDays(cursor, 1)
  }

  return dates
}

export function formatIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split('-').map((part) => Number.parseInt(part, 10))
  if (!year || !month || !day) return startOfToday()
  return new Date(year, month - 1, day)
}

export function formatMonthDay(date: Date): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit'
  }).format(date)
}
