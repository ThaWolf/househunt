import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'

const nav = [
  { to: '/search', label: 'Buscar' },
  { to: '/interest', label: 'Interés' },
  { to: '/archived', label: 'Archivadas' },
  { to: '/calendar', label: 'Calendario' },
]

export function Layout() {
  const { user, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-line bg-surface/90 backdrop-blur-sm sticky top-0 z-40">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <NavLink to={isAuthenticated ? '/search' : '/'} className="group flex items-baseline gap-2 no-underline">
            <span className="font-display text-3xl font-bold tracking-tight text-ink group-hover:text-accent transition-colors">
              Househunt
            </span>
            <span className="hidden sm:inline font-mono text-[10px] uppercase text-ink-muted">
              GBA → nacional
            </span>
          </NavLink>

          {isAuthenticated && (
            <nav className="flex flex-wrap items-center gap-1 sm:gap-2">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `rounded-md px-2.5 py-1.5 text-sm no-underline transition-colors ${
                      isActive
                        ? 'bg-accent-soft text-accent font-medium'
                        : 'text-ink-muted hover:text-ink hover:bg-paper'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          )}

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="hidden md:inline font-mono text-xs text-ink-muted truncate max-w-[140px]">
                  {user.email}
                </span>
                <button
                  type="button"
                  className="hh-btn-ghost text-xs py-1.5"
                  onClick={() => {
                    void logout().then(() => navigate('/login'))
                  }}
                >
                  Salir
                </button>
              </>
            ) : (
              <NavLink to="/login" className="hh-btn-primary text-xs no-underline">
                Entrar
              </NavLink>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1 mx-auto w-full max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
