import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const SelectionContext = createContext(null)

const STORAGE_KEY = 'podcastSources-1'

export function SelectionProvider({ children }) {
  const [selectedIds, setSelectedIds] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return new Set(stored ? JSON.parse(stored) : [])
  })

  const isSelectMode = selectedIds.size > 0

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...selectedIds]))
  }, [selectedIds])

  const toggle = useCallback((id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  const selectMany = useCallback((ids) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      for (const id of ids) {
        next.add(id)
      }
      return next
    })
  }, [])

  const clear = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  const isSelected = useCallback((id) => selectedIds.has(id), [selectedIds])

  const value = {
    selectedIds,
    isSelectMode,
    toggle,
    selectMany,
    clear,
    isSelected,
  }

  return (
    <SelectionContext.Provider value={value}>
      {children}
    </SelectionContext.Provider>
  )
}

export function useSelection() {
  const context = useContext(SelectionContext)
  if (!context) {
    throw new Error('useSelection must be used within a SelectionProvider')
  }
  return context
}
