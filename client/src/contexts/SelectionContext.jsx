import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const SelectionContext = createContext(null)

const STORAGE_KEY = 'podcastSources-1'

export function SelectionProvider({ children }) {
  const [selectedIds, setSelectedIds] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    const parsed = stored ? JSON.parse(stored) : []
    return new Set(parsed.filter((id) => id.startsWith('article-')))
  })
  const [disabledIds, setDisabledIds] = useState(() => new Set())

  const isSelectMode = selectedIds.size > 0

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...selectedIds]))
  }, [selectedIds])

  const toggle = useCallback((id) => {
    if (disabledIds.has(id)) return
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [disabledIds])

  const selectMany = useCallback((ids) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      for (const id of ids) {
        if (!disabledIds.has(id)) {
          next.add(id)
        }
      }
      return next
    })
  }, [disabledIds])

  const deselectMany = useCallback((ids) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      for (const id of ids) {
        next.delete(id)
      }
      return next
    })
  }, [])

  const registerSelectable = useCallback((id, isDisabled) => {
    setDisabledIds(prev => {
      const next = new Set(prev)
      if (isDisabled) {
        next.add(id)
      } else {
        next.delete(id)
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
    deselectMany,
    registerSelectable,
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
