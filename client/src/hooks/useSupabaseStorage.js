import { useCallback, useEffect, useRef, useState } from 'react'

const changeListenersByKey = new Map()
const readCache = new Map()
const inflightReads = new Map()

function emitChange(key) {
  const listeners = changeListenersByKey.get(key)
  if (listeners) {
    listeners.forEach(listener => {
      try {
        listener()
      } catch (error) {
        console.error(`Storage listener failed: ${error.message}`)
      }
    })
  }

  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('supabase-storage-change', { detail: { key } }))
  }
}

function subscribe(key, listener) {
  if (!changeListenersByKey.has(key)) {
    changeListenersByKey.set(key, new Set())
  }
  changeListenersByKey.get(key).add(listener)

  return () => {
    const listeners = changeListenersByKey.get(key)
    if (listeners) {
      listeners.delete(listener)
      if (listeners.size === 0) {
        changeListenersByKey.delete(key)
      }
    }
  }
}

async function readValue(key, defaultValue) {
  if (typeof window === 'undefined') return defaultValue

  if (readCache.has(key)) {
    return readCache.get(key)
  }

  if (inflightReads.has(key)) {
    return inflightReads.get(key)
  }

  const readPromise = (async () => {
    try {
      let value = defaultValue

      if (key.startsWith('cache:')) {
        const response = await window.fetch(`/api/storage/setting/${key}`)
        const data = await response.json()
        if (data.success) {
          value = data.value
        }
      } else if (key.startsWith('newsletters:scrapes:')) {
        const date = key.split(':')[2]
        const response = await window.fetch(`/api/storage/daily/${date}`)
        const data = await response.json()
        if (data.success) {
          value = data.payload
        }
      } else {
        console.warn(`Unknown storage key pattern: ${key}`)
      }

      readCache.set(key, value)
      return value

    } catch (error) {
      console.error(`Failed to read from storage: ${error.message}`)
      return defaultValue
    } finally {
      inflightReads.delete(key)
    }
  })()

  inflightReads.set(key, readPromise)
  return readPromise
}

async function writeValue(key, value) {
  if (typeof window === 'undefined') return

  try {
    if (key.startsWith('cache:')) {
      const response = await window.fetch(`/api/storage/setting/${key}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to write setting')
      }

      readCache.set(key, value)
      emitChange(key)
      return
    }

    if (key.startsWith('newsletters:scrapes:')) {
      const date = key.split(':')[2]
      const response = await window.fetch(`/api/storage/daily/${date}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payload: value })
      })

      const data = await response.json()
      if (!data.success) {
        throw new Error(data.error || 'Failed to write daily cache')
      }

      readCache.set(key, value)
      emitChange(key)
      return
    }

    throw new Error(`Unknown storage key pattern: ${key}`)

  } catch (error) {
    console.error(`Failed to persist to storage: ${error.message}`)
    throw error
  }
}

export function useSupabaseStorage(key, defaultValue) {
  const [value, setValue] = useState(defaultValue)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const valueRef = useRef(defaultValue)

  useEffect(() => {
    let cancelled = false

    readValue(key, defaultValue).then(loadedValue => {
      if (!cancelled) {
        setValue(loadedValue)
        valueRef.current = loadedValue
        setLoading(false)
      }
    }).catch(err => {
      if (!cancelled) {
        console.error(`Failed to load storage value for ${key}:`, err)
        setError(err)
        setValue(defaultValue)
        valueRef.current = defaultValue
        setLoading(false)
      }
    })

    return () => {
      cancelled = true
    }
  }, [key])

  useEffect(() => {
    const handleChange = () => {
      readValue(key, defaultValue).then(newValue => {
        setValue(newValue)
        valueRef.current = newValue
      }).catch(err => {
        console.error(`Failed to reload storage value for ${key}:`, err)
      })
    }

    return subscribe(key, handleChange)
  }, [key])

  const setValueAsync = useCallback(async (nextValue) => {
    if (typeof window === 'undefined') return

    setLoading(true)
    setError(null)

    try {
      const previous = valueRef.current
      const resolved = typeof nextValue === 'function' ? nextValue(previous) : nextValue

      if (resolved === previous) {
        setLoading(false)
        return
      }

      valueRef.current = resolved
      await writeValue(key, resolved)
      setValue(resolved)
      setLoading(false)

    } catch (err) {
      console.error(`Failed to set storage value for ${key}:`, err)
      setError(err)
      setLoading(false)
      throw err
    }
  }, [key])

  const remove = useCallback(async () => {
    await setValueAsync(undefined)
  }, [setValueAsync])

  return [value, setValueAsync, remove, { loading, error }]
}
