/**
 * useLocalStorage - Reactive localStorage composable
 * Automatically syncs Vue ref with localStorage
 */
import { ref, watch } from 'vue'

export function useLocalStorage(key, defaultValue) {
  // Initialize from storage or use default
  const data = ref(readFromStorage(key, defaultValue))

  // Watch for changes and persist to localStorage
  watch(
    data,
    (newValue) => {
      try {
        localStorage.setItem(key, JSON.stringify(newValue))
      } catch (error) {
        console.error(`Failed to persist to localStorage: ${error.message}`)
      }
    },
    { deep: true }  // Watch nested objects/arrays
  )

  /**
   * Read and parse data from localStorage
   */
  function readFromStorage(storageKey, fallback) {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw === null) return fallback
      return JSON.parse(raw)
    } catch (error) {
      console.error(`Failed to read from localStorage: ${error.message}`)
      return fallback
    }
  }

  /**
   * Clear this specific key from storage
   */
  function clear() {
    localStorage.removeItem(key)
    data.value = defaultValue
  }

  return { data, clear }
}
