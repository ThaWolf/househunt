import { useMemo, useState } from 'react'
import type { ImageRef } from '@/api/types'
import { galleryImages } from '@/lib/format'

type Props = {
  images: ImageRef[]
  alt?: string
}

export function ImageGallery({ images, alt = '' }: Props) {
  const sorted = useMemo(() => galleryImages(images), [images])
  const [index, setIndex] = useState(0)
  const [broken, setBroken] = useState<Set<number>>(() => new Set())

  const usable = sorted.filter((_, i) => !broken.has(i))
  const hasImages = usable.length > 0
  const safeIndex = Math.min(index, Math.max(usable.length - 1, 0))
  const current = hasImages ? usable[safeIndex] : null

  function markBroken(orderIndex: number) {
    setBroken((prev) => new Set(prev).add(orderIndex))
  }

  return (
    <div className="relative -mx-4 sm:mx-0 mb-6 overflow-hidden sm:rounded-lg bg-ink min-h-[240px]">
      {current ? (
        <img
          key={current.url}
          src={current.url}
          alt={alt}
          className="h-[280px] sm:h-[400px] w-full object-cover opacity-95"
          onError={() => {
            const idx = sorted.findIndex((img) => img.url === current.url)
            if (idx >= 0) markBroken(idx)
          }}
        />
      ) : (
        <div className="flex h-[280px] sm:h-[400px] items-center justify-center text-white/40 font-mono text-sm">
          Sin imagen
        </div>
      )}

      {usable.length > 1 && (
        <>
          <button
            type="button"
            className="absolute left-2 top-1/2 -translate-y-1/2 rounded bg-ink/60 px-2 py-1 text-white text-sm hover:bg-ink/80"
            aria-label="Imagen anterior"
            onClick={() =>
              setIndex((i) => (i - 1 + usable.length) % usable.length)
            }
          >
            ‹
          </button>
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded bg-ink/60 px-2 py-1 text-white text-sm hover:bg-ink/80"
            aria-label="Imagen siguiente"
            onClick={() => setIndex((i) => (i + 1) % usable.length)}
          >
            ›
          </button>
          <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5">
            {usable.map((img, i) => (
              <button
                key={img.url + i}
                type="button"
                aria-label={`Foto ${i + 1}`}
                className={`h-2 w-2 rounded-full ${
                  i === safeIndex ? 'bg-white' : 'bg-white/40'
                }`}
                onClick={() => setIndex(i)}
              />
            ))}
          </div>
        </>
      )}

      {usable.length > 1 && (
        <p className="absolute right-3 top-3 rounded bg-ink/50 px-1.5 py-0.5 font-mono text-[10px] text-white/80">
          {safeIndex + 1}/{usable.length}
        </p>
      )}
    </div>
  )
}
