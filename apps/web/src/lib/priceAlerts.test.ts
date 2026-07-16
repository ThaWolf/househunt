import { describe, expect, it } from 'vitest'
import {
  isUnusualHousePrice,
  UNUSUAL_PRICE_BANNER,
} from '@/lib/priceAlerts'

describe('isUnusualHousePrice', () => {
  it('flags low USD house prices', () => {
    expect(
      isUnusualHousePrice({ amount: 12000, currency: 'USD', period: null }, 'house'),
    ).toBe(true)
  })

  it('ignores apartments, ARS, null amount, and higher USD', () => {
    expect(
      isUnusualHousePrice({ amount: 12000, currency: 'USD', period: null }, 'apartment'),
    ).toBe(false)
    expect(
      isUnusualHousePrice({ amount: 12000, currency: 'ARS', period: null }, 'house'),
    ).toBe(false)
    expect(
      isUnusualHousePrice({ amount: null, currency: 'USD', period: null }, 'house'),
    ).toBe(false)
    expect(
      isUnusualHousePrice({ amount: 20000, currency: 'USD', period: null }, 'house'),
    ).toBe(false)
  })

  it('exports banner copy', () => {
    expect(UNUSUAL_PRICE_BANNER).toMatch(/Precio inusual/)
  })
})
