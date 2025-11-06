import { useState, useEffect, useCallback, useRef } from 'react'

export function useLocalStorage(key, defaultValue) {
  const [value, setValue] = useState(() => {
    try {
      const item = localStorage.getItem(key)
      return item ? JSON.parse(item) : defaultValue
    } catch (error) {
      console.error(`Failed to read from localStorage: ${error.message}`)
      return defaultValue
    }
  })

  const valueRef = useRef(value)

  useEffect(() => {
    valueRef.current = value
  }, [value])

  useEffect(() => {
    try {
      const currentStored = localStorage.getItem(key)
      const currentValue = currentStored ? JSON.parse(currentStored) : null
      const newValueStr = JSON.stringify(value)
      const currentValueStr = JSON.stringify(currentValue)

      if (newValueStr !== currentValueStr) {
        localStorage.setItem(key, newValueStr)
        window.dispatchEvent(new CustomEvent('local-storage-change', { detail: { key } }))
      }
    } catch (error) {
      console.error(`Failed to persist to localStorage: ${error.message}`)
    }
  }, [key, value])

  useEffect(() => {
    const handleStorageChange = (event) => {
      if (event.detail?.key === key) {
        try {
          const item = localStorage.getItem(key)
          const newValue = item ? JSON.parse(item) : defaultValue
          const newValueStr = JSON.stringify(newValue)
          const currentValueStr = JSON.stringify(valueRef.current)

          if (newValueStr !== currentValueStr) {
            setValue(newValue)
          }
        } catch (error) {
          console.error(`Failed to sync from localStorage: ${error.message}`)
        }
      }
    }

    window.addEventListener('local-storage-change', handleStorageChange)
    return () => window.removeEventListener('local-storage-change', handleStorageChange)
  }, [key, defaultValue])

  const remove = useCallback(() => {
    localStorage.removeItem(key)
    setValue(defaultValue)
  }, [key, defaultValue])

  return [value, setValue, remove]
}
