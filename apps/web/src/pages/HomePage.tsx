import { Link } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

export function HomePage() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="relative animate-fade-in min-h-[70vh] flex flex-col justify-center">
      <div className="max-w-xl">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent mb-3">
          Compra · GBA primero
        </p>
        <h1 className="font-display text-6xl sm:text-7xl font-bold text-ink leading-[0.95] mb-4">
          Househunt
        </h1>
        <p className="text-lg text-ink-muted mb-8 max-w-md">
          Un solo lugar para buscar casas en los portales de Argentina, scorearlas
          y seguir visitas.
        </p>
        <div className="flex flex-wrap gap-3">
          {isAuthenticated ? (
            <Link to="/search" className="hh-btn-accent no-underline text-base px-6 py-3">
              Ir a buscar
            </Link>
          ) : (
            <>
              <Link to="/login" className="hh-btn-accent no-underline text-base px-6 py-3">
                Entrar
              </Link>
              <Link to="/register" className="hh-btn-ghost no-underline text-base px-6 py-3">
                Crear cuenta
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
