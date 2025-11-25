import { useCallback, useMemo } from 'react'
import { useSupabaseStorage } from './useSupabaseStorage'
import { STORAGE_KEYS } from '../lib/storageKeys'

export function useFoldState(containerId) {
  const [foldedIds, setFoldedIds] = useSupabaseStorage(STORAGE_KEYS.FOLDED_CONTAINERS, [])

  const isFolded = useMemo(() => {
    return Array.isArray(foldedIds) && foldedIds.includes(containerId)
  }, [foldedIds, containerId])

  const toggleFold = useCallback(() => {
    setFoldedIds(current => {
      const currentArray = Array.isArray(current) ? current : []
      if (currentArray.includes(containerId)) {
        return currentArray.filter(id => id !== containerId)
      }
      return [...currentArray, containerId]
    })
  }, [containerId, setFoldedIds])

  return { isFolded, toggleFold }
}
