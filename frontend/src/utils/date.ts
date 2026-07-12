export function startOfToday(): Date {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), now.getDate())
}

export function parseIsoDate(value: string): Date {
  const [year, month, day] = value.split('-').map((item) => Number(item))
  if (!year || !month || !day) return startOfToday()
  return new Date(year, month - 1, day)
}

export function formatIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function formatMonthDay(date: Date | string): string {
  const value = typeof date === 'string' ? parseIsoDate(date) : date
  return `${String(value.getMonth() + 1).padStart(2, '0')}/${String(value.getDate()).padStart(2, '0')}`
}

export function addDays(date: Date, offset: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + offset)
  return next
}

export function eachDateInRange(start: Date, end: Date): string[] {
  const dates: string[] = []
  const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate())
  const last = new Date(end.getFullYear(), end.getMonth(), end.getDate())

  while (cursor <= last) {
    dates.push(formatIsoDate(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }
  return dates
}

