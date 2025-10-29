/**
 * useCacheSettings - Manages cache toggle state
 * Provides reactive access to cache enabled/disabled setting
 */
import { computed } from 'vue'
import { useLocalStorage } from './useLocalStorage'

const CACHE_SETTING_KEY = 'cache:enabled'

export function useCacheSettings() {
  const { data: enabled } = useLocalStorage(CACHE_SETTING_KEY, true)

  const statusText = computed(() =>
    enabled.value ? '(enabled)' : '(disabled)'
  )

  function toggle() {
    enabled.value = !enabled.value
  }

  return {
    enabled,
    statusText,
    toggle
  }
}
