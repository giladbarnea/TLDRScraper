import { useCallback, useSyncExternalStore } from 'react'

const listenersByKey = new Map()
const snapshotCache = new Map()

function getListeners(key) {
  let listeners = listenersByKey.get(key)
  if (!listeners) {
    listeners = new Set()
    listenersByKey.set(key, listeners)
  }
  return listeners
}

function emitChange(key) {
  const listeners = listenersByKey.get(key)
  if (listeners) {
    listeners.forEach(listener => {
      try {
        listener()
      } catch (error) {
        console.error(`localStorage listener failed: ${error.message}`)
      }
    })
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('local-storage-change', { detail: { key } }))
  }
}

function readValue(key, defaultValue) {
  if (typeof window === 'undefined') return defaultValue

  try {
    const raw = window.localStorage.getItem(key)

    const cached = snapshotCache.get(key)
    if (raw === null) {
      if (cached && cached.raw === null) {
        return cached.value
      }
      snapshotCache.set(key, { raw: null, value: defaultValue })
      return defaultValue
    }

    if (cached && cached.raw === raw) {
      return cached.value
    }

    const parsed = JSON.parse(raw)
    snapshotCache.set(key, { raw, value: parsed })
    return parsed
  } catch (error) {
    console.error(`Failed to read from localStorage: ${error.message}`)
    snapshotCache.delete(key)
    return defaultValue
  }
}

function subscribe(key, listener) {
  const listeners = getListeners(key)
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) {
      listenersByKey.delete(key)
    }
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (!event.key) return
    snapshotCache.delete(event.key)
    emitChange(event.key)
  })
}

export function useLocalStorage(key, defaultValue) {
  const getSnapshot = useCallback(() => readValue(key, defaultValue), [key, defaultValue])

  const value = useSyncExternalStore(
    useCallback((listener) => subscribe(key, listener), [key]),
    getSnapshot,
    getSnapshot
  )

  const setValue = useCallback((nextValue) => {
    if (typeof window === 'undefined') return

    const previous = readValue(key, defaultValue)
    const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue

    if (resolved === previous) {
      return
    }

    try {
      if (resolved === undefined) {
        window.localStorage.removeItem(key)
        snapshotCache.delete(key)
      } else {
        const raw = JSON.stringify(resolved)
        window.localStorage.setItem(key, raw)
        snapshotCache.set(key, { raw, value: resolved })
      }
      emitChange(key)
    } catch (error) {
      console.error(`Failed to persist to localStorage: ${error.message}`)
    }
  }, [key, defaultValue])

  const remove = useCallback(() => {
    if (typeof window === 'undefined') return
    try {
      window.localStorage.removeItem(key)
      snapshotCache.delete(key)
      emitChange(key)
    } catch (error) {
      console.error(`Failed to remove from localStorage: ${error.message}`)
    }
  }, [key])

  return [value, setValue, remove]
}
