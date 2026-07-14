import { useMemo, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { searchApi } from '@/api/endpoints'
import type {
  Currency,
  GeoPlace,
  Location,
  PortalId,
  PropertyType,
  SearchFilters,
} from '@/api/types'
import { ALL_PORTALS, PORTAL_LABELS } from '@/api/types'
import { SearchLoadingProgress } from '@/components/LoadingState'
import { LocationAutocomplete } from '@/components/LocationAutocomplete'

const LAST_SEARCH_KEY = 'hh_last_search'

function toLocationBody(place: GeoPlace): Location {
  return {
    query: place.query || place.label,
    locality: place.locality,
    district: place.district ?? null,
    province: place.province,
    country: 'AR',
    placeId: place.placeId ?? null,
  }
}

export function SearchPage() {
  const navigate = useNavigate()
  const [propertyType, setPropertyType] = useState<PropertyType>('house')
  const [locationText, setLocationText] = useState('')
  const [location, setLocation] = useState<Location | null>(null)
  const [gbaWide, setGbaWide] = useState(true)
  const [priceMin, setPriceMin] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [currency, setCurrency] = useState<Currency>('USD')
  const [roomsMin, setRoomsMin] = useState('')
  const [bathroomsMin, setBathroomsMin] = useState('')
  const [coveredMin, setCoveredMin] = useState('')
  const [totalMin, setTotalMin] = useState('')
  const [parkingMin, setParkingMin] = useState('')
  const [query, setQuery] = useState('')
  const [portals, setPortals] = useState<PortalId[]>([...ALL_PORTALS])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const filters: SearchFilters = useMemo(() => {
    const f: SearchFilters = {
      operation: 'buy',
      propertyType,
      location: gbaWide || !location ? null : location,
      price: {
        min: priceMin ? Number(priceMin) : null,
        max: priceMax ? Number(priceMax) : null,
        currency,
      },
      rooms: { min: roomsMin ? Number(roomsMin) : null },
      bathrooms: { min: bathroomsMin ? Number(bathroomsMin) : null },
      area: {
        coveredM2Min: coveredMin ? Number(coveredMin) : null,
        totalM2Min: totalMin ? Number(totalMin) : null,
      },
      parking: { min: parkingMin ? Number(parkingMin) : null },
      portals,
      query: query || null,
    }
    return f
  }, [
    propertyType,
    location,
    gbaWide,
    priceMin,
    priceMax,
    currency,
    roomsMin,
    bathroomsMin,
    coveredMin,
    totalMin,
    parkingMin,
    portals,
    query,
  ])

  function togglePortal(id: PortalId) {
    setPortals((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id],
    )
  }

  function onSelectPlace(place: GeoPlace) {
    setLocation(toLocationBody(place))
    setGbaWide(false)
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!gbaWide && !location) {
      setError('Elegí una ubicación del autocomplete, o marcá “Buscar en todo GBA”')
      return
    }
    if (!portals.length) {
      setError('Seleccioná al menos un portal')
      return
    }
    setBusy(true)
    try {
      const result = await searchApi.search(filters)
      sessionStorage.setItem(LAST_SEARCH_KEY, JSON.stringify(result))
      navigate('/results')
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Error al buscar propiedades',
      )
    } finally {
      setBusy(false)
    }
  }

  if (busy) {
    return (
      <SearchLoadingProgress label="Buscando en portales… esto puede tardar" />
    )
  }

  return (
    <div className="animate-fade-in max-w-3xl">
      <h1 className="font-display text-4xl font-bold text-ink mb-1">Buscar</h1>
      <p className="text-sm text-ink-muted mb-6">
        Ubicación con autocomplete → scrap on-demand. Sin ubicación = preset GBA.
      </p>

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-lg border border-line bg-surface p-5"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="hh-label">Tipo</label>
            <select
              className="hh-input"
              value={propertyType}
              onChange={(e) => setPropertyType(e.target.value as PropertyType)}
            >
              <option value="house">Casa</option>
              <option value="apartment">Depto</option>
              <option value="land">Terreno</option>
              <option value="other">Otro</option>
            </select>
          </div>
          <div>
            <label className="hh-label">Operación</label>
            <input className="hh-input" value="Compra (venta)" disabled />
          </div>
        </div>

        <fieldset className="space-y-3">
          <LocationAutocomplete
            value={location}
            inputText={locationText}
            onInputTextChange={setLocationText}
            onSelect={onSelectPlace}
            onClearLocation={() => setLocation(null)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={gbaWide}
              onChange={(e) => {
                const checked = e.target.checked
                setGbaWide(checked)
                if (checked) {
                  setLocation(null)
                  setLocationText('')
                }
              }}
            />
            Buscar en todo GBA (limpia ubicación)
          </label>
        </fieldset>

        <div className="grid gap-3 sm:grid-cols-3">
          <div>
            <label className="hh-label">Precio min</label>
            <input
              type="number"
              className="hh-input"
              value={priceMin}
              onChange={(e) => setPriceMin(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Precio max</label>
            <input
              type="number"
              className="hh-input"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Moneda</label>
            <select
              className="hh-input"
              value={currency}
              onChange={(e) => setCurrency(e.target.value as Currency)}
            >
              <option value="USD">USD</option>
              <option value="ARS">ARS</option>
            </select>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-4">
          <div>
            <label className="hh-label" htmlFor="rooms-min">
              Habitaciones mín.
            </label>
            <input
              id="rooms-min"
              type="number"
              min={0}
              className="hh-input"
              value={roomsMin}
              onChange={(e) => setRoomsMin(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Baños mín.</label>
            <input
              type="number"
              className="hh-input"
              value={bathroomsMin}
              onChange={(e) => setBathroomsMin(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Cubiertos m²</label>
            <input
              type="number"
              className="hh-input"
              value={coveredMin}
              onChange={(e) => setCoveredMin(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Total m²</label>
            <input
              type="number"
              className="hh-input"
              value={totalMin}
              onChange={(e) => setTotalMin(e.target.value)}
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="hh-label">Cocheras mín.</label>
            <input
              type="number"
              className="hh-input"
              value={parkingMin}
              onChange={(e) => setParkingMin(e.target.value)}
            />
          </div>
          <div>
            <label className="hh-label">Texto libre</label>
            <input
              className="hh-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="pileta, jardín…"
            />
          </div>
        </div>

        <fieldset>
          <legend className="hh-label">Portales</legend>
          <div className="flex flex-wrap gap-3">
            {ALL_PORTALS.map((id) => (
              <label key={id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={portals.includes(id)}
                  onChange={() => togglePortal(id)}
                />
                {PORTAL_LABELS[id]}
              </label>
            ))}
          </div>
        </fieldset>

        {error && (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="hh-btn-accent">
          Confirmar y buscar
        </button>
      </form>
    </div>
  )
}

export { LAST_SEARCH_KEY }
