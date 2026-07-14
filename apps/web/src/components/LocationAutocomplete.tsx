import { useEffect, useId, useRef, useState } from 'react'
import { ApiError } from '@/api/client'
import { geoApi } from '@/api/endpoints'
import type { GeoPlace, Location } from '@/api/types'

type Props = {
  value: Location | null
  inputText: string
  onInputTextChange: (text: string) => void
  onSelect: (place: GeoPlace) => void
  onClearLocation: () => void
  disabled?: boolean
}

export function LocationAutocomplete({
  value,
  inputText,
  onInputTextChange,
  onSelect,
  onClearLocation,
  disabled,
}: Props) {
  const listId = useId()
  const [suggestions, setSuggestions] = useState<GeoPlace[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [hint, setHint] = useState<string | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  useEffect(() => {
    const q = inputText.trim()
    if (debounceRef.current) clearTimeout(debounceRef.current)
    abortRef.current?.abort()

    if (q.length < 1) {
      setSuggestions([])
      setLoading(false)
      setHint(null)
      return
    }

    // Skip refetch if current selection already matches display text
    if (value && (value.query === q || value.locality === q)) {
      setSuggestions([])
      setLoading(false)
      return
    }

    debounceRef.current = setTimeout(() => {
      const ac = new AbortController()
      abortRef.current = ac
      setLoading(true)
      setHint(null)
      void geoApi
        .suggest(q, ac.signal)
        .then((res) => {
          setSuggestions(res.items)
          setOpen(res.items.length > 0)
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === 'AbortError') return
          setSuggestions([])
          setHint(
            err instanceof ApiError
              ? err.message
              : 'No se pudo cargar sugerencias',
          )
        })
        .finally(() => setLoading(false))
    }, 250)

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      abortRef.current?.abort()
    }
  }, [inputText, value])

  function pick(place: GeoPlace) {
    onSelect(place)
    onInputTextChange(place.label)
    setSuggestions([])
    setOpen(false)
  }

  return (
    <div ref={wrapRef} className="relative">
      <label className="hh-label" htmlFor="hh-location">
        Ubicación / localidad
      </label>
      <input
        id="hh-location"
        className="hh-input"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        autoComplete="off"
        disabled={disabled}
        value={inputText}
        placeholder="City Bell, Gonnet, Pilar…"
        onChange={(e) => {
          onInputTextChange(e.target.value)
          if (value) onClearLocation()
        }}
        onFocus={() => {
          if (suggestions.length) setOpen(true)
        }}
      />
      {loading && (
        <p className="mt-1 font-mono text-[10px] text-ink-muted">Buscando…</p>
      )}
      {hint && (
        <p className="mt-1 text-xs text-warn" role="status">
          {hint}
        </p>
      )}
      {open && suggestions.length > 0 && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded border border-line bg-surface shadow-md"
        >
          {suggestions.map((place) => (
            <li key={place.placeId ?? place.label} role="option">
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-accent-soft"
                onClick={() => pick(place)}
              >
                {place.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      {value && (
        <p className="mt-1 font-mono text-[10px] text-ink-muted">
          Seleccionado: {value.locality}
          {value.district ? ` · ${value.district}` : ''} · {value.province}
        </p>
      )}
    </div>
  )
}
