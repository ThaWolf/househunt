import { useActiveList } from '@/context/ActiveListContext'

export function ListSelector() {
  const { lists, activeListId, setActiveListId, loading } = useActiveList()

  if (loading && !lists.length) {
    return (
      <select className="hh-input py-1 text-sm w-[200px]" disabled>
        <option>Cargando listas…</option>
      </select>
    )
  }

  if (lists.length <= 1) {
    const only = lists[0]
    if (!only) return null
    return (
      <span className="text-sm text-ink-muted font-mono">
        {only.name}
        {only.memberCount > 1 ? ` · ${only.memberCount} miembros` : ''}
      </span>
    )
  }

  return (
    <select
      className="hh-input py-1 text-sm w-[220px]"
      value={activeListId ?? ''}
      onChange={(e) => setActiveListId(e.target.value)}
      aria-label="Lista de interés activa"
    >
      {lists.map((l) => (
        <option key={l.id} value={l.id}>
          {l.name} ({l.role})
        </option>
      ))}
    </select>
  )
}
