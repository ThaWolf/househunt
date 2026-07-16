import type { Money, PropertyType } from '@/api/types'

const UNUSUAL_HOUSE_USD_THRESHOLD = 15_000

/** Casa en USD por debajo del umbral — posible error de parseo. */
export function isUnusualHousePrice(
  price: Money | null | undefined,
  propertyType: PropertyType | undefined,
): boolean {
  if (propertyType !== 'house') return false
  if (price?.amount == null) return false
  if (price.currency !== 'USD') return false
  return price.amount < UNUSUAL_HOUSE_USD_THRESHOLD
}

export const UNUSUAL_PRICE_BANNER =
  'Precio inusual — puede ser error de parseo. Confirmá en el portal.'
