import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ApiError } from '@/api/client'
import { interestListsApi } from '@/api/endpoints'
import type { InterestListSummary } from '@/api/types'

const STORAGE_KEY = 'househunt.activeListId'

type ActiveListContextValue = {
  lists: InterestListSummary[]
  activeListId: string | null
  activeList: InterestListSummary | null
  loading: boolean
  error: string | null
  setActiveListId: (id: string) => void
  refreshLists: () => Promise<void>
}

const ActiveListContext = createContext<ActiveListContextValue | null>(null)

export function ActiveListProvider({ children }: { children: ReactNode }) {
  const [lists, setLists] = useState<InterestListSummary[]>([])
  const [activeListId, setActiveListIdState] = useState<string | null>(() =>
    localStorage.getItem(STORAGE_KEY),
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshLists = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await interestListsApi.list()
      setLists(res.items)
      const stored = localStorage.getItem(STORAGE_KEY)
      const pick =
        res.items.find((l) => l.id === stored)?.id ??
        res.items.find((l) => l.role === 'owner')?.id ??
        res.items[0]?.id ??
        null
      if (pick) {
        setActiveListIdState(pick)
        localStorage.setItem(STORAGE_KEY, pick)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Error al cargar listas')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshLists()
  }, [refreshLists])

  const setActiveListId = useCallback((id: string) => {
    setActiveListIdState(id)
    localStorage.setItem(STORAGE_KEY, id)
  }, [])

  const activeList = useMemo(
    () => lists.find((l) => l.id === activeListId) ?? null,
    [lists, activeListId],
  )

  const value = useMemo(
    () => ({
      lists,
      activeListId,
      activeList,
      loading,
      error,
      setActiveListId,
      refreshLists,
    }),
    [lists, activeListId, activeList, loading, error, setActiveListId, refreshLists],
  )

  return (
    <ActiveListContext.Provider value={value}>{children}</ActiveListContext.Provider>
  )
}

export function useActiveList() {
  const ctx = useContext(ActiveListContext)
  if (!ctx) {
    throw new Error('useActiveList must be used within ActiveListProvider')
  }
  return ctx
}
