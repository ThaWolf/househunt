import type { Money, Address, InterestFlags, ImageRef } from '@/api/types'

/** Prefer real source/proxied URLs; skip typed placeholders when possible. */
export function isRealImage(img: ImageRef): boolean {
  if (img.kind === 'placeholder') return false
  if (!img.url) return false
  const u = img.url.toLowerCase()
  if (u.startsWith('data:') && u.includes('placeholder')) return false
  return true
}

export function formatMoney(price?: Money | null): string {
  if (!price || price.amount == null) return 'Consultar'
  const currency = price.currency ?? 'USD'
  try {
    return new Intl.NumberFormat('es-AR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(price.amount)
  } catch {
    return `${currency} ${price.amount.toLocaleString('es-AR')}`
  }
}

export function formatLocation(address?: Address | null): string {
  if (!address) return '—'
  const parts = [
    address.neighborhood,
    address.locality,
    address.province,
  ].filter(Boolean)
  if (parts.length) return parts.join(', ')
  return address.raw ?? '—'
}

export function interestBadgeLabel(
  interest?: InterestFlags | null,
): 'interés' | 'archivada' | null {
  if (!interest?.state) return null
  if (interest.state === 'archived') return 'archivada'
  if (interest.state === 'active') return 'interés'
  return null
}

export function primaryImageUrl(images?: ImageRef[] | null): string | null {
  if (!images?.length) return null
  const sorted = [...images].sort((a, b) => a.order - b.order)
  const real = sorted.find(isRealImage)
  return (real ?? sorted[0])?.url ?? null
}

export function galleryImages(images?: ImageRef[] | null): ImageRef[] {
  if (!images?.length) return []
  const sorted = [...images].sort((a, b) => a.order - b.order)
  const real = sorted.filter(isRealImage)
  return real.length > 0 ? real : sorted
}

/** Local datetime-local value ↔ ISO */
export function toLocalInputValue(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function fromLocalInputValue(local: string): string {
  return new Date(local).toISOString()
}

export function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

export function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999)
}

export function daysInMonthGrid(anchor: Date): Date[] {
  const start = startOfMonth(anchor)
  const end = endOfMonth(anchor)
  const startDow = (start.getDay() + 6) % 7 // Mon=0
  const cells: Date[] = []
  for (let i = 0; i < startDow; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() - (startDow - i))
    cells.push(d)
  }
  for (let day = 1; day <= end.getDate(); day++) {
    cells.push(new Date(anchor.getFullYear(), anchor.getMonth(), day))
  }
  while (cells.length % 7 !== 0) {
    const last = cells[cells.length - 1]!
    const n = new Date(last)
    n.setDate(n.getDate() + 1)
    cells.push(n)
  }
  return cells
}
