/**
 * useSummary - Handles summary and TLDR fetching, caching, and rendering
 * Works for both 'summary' and 'tldr' types
 */
import { ref, computed } from 'vue'
import { useArticleState } from './useArticleState'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

export function useSummary(date, url, type = 'summary') {
  const { article } = useArticleState(date, url)
  const loading = ref(false)
  const expanded = ref(false)
  const effort = ref('low')

  // Get the summary/tldr data from article
  const data = computed(() => article.value?.[type])

  const status = computed(() => data.value?.status || 'unknown')

  const markdown = computed(() => data.value?.markdown || '')

  // Convert markdown to sanitized HTML
  const html = computed(() => {
    if (!markdown.value) return ''
    try {
      const rawHtml = marked.parse(markdown.value)
      return DOMPurify.sanitize(rawHtml)
    } catch (error) {
      console.error('Failed to parse markdown:', error)
      return ''
    }
  })

  const errorMessage = computed(() => data.value?.errorMessage || null)

  const isAvailable = computed(() => status.value === 'available' && markdown.value)

  const isLoading = computed(() => status.value === 'creating' || loading.value)

  const isError = computed(() => status.value === 'error')

  // Button label based on state
  const buttonLabel = computed(() => {
    if (isLoading.value) return 'Loading...'
    if (expanded.value) return 'Hide'
    if (isAvailable.value) return 'Available'
    if (isError.value) return 'Retry'
    return type === 'summary' ? 'Summarize' : 'TLDR'
  })

  /**
   * Fetch summary/tldr from API
   */
  async function fetch(summaryEffort = effort.value) {
    if (!article.value) return

    loading.value = true
    effort.value = summaryEffort

    // Update status to creating
    if (!article.value[type]) {
      article.value[type] = {}
    }
    article.value[type].status = 'creating'

    const endpoint = type === 'summary' ? '/api/summarize-url' : '/api/tldr-url'

    try {
      const response = await window.fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          summary_effort: summaryEffort
        })
      })

      const result = await response.json()

      if (result.success) {
        // Update article with successful result
        article.value[type] = {
          status: 'available',
          markdown: result[`${type}_markdown`] || '',
          effort: summaryEffort,
          checkedAt: new Date().toISOString(),
          errorMessage: null
        }
        expanded.value = true
      } else {
        // Update with error
        article.value[type].status = 'error'
        article.value[type].errorMessage = result.error || `Failed to fetch ${type}`
      }
    } catch (error) {
      // Network error
      article.value[type].status = 'error'
      article.value[type].errorMessage = error.message || 'Network error'
      console.error(`Failed to fetch ${type}:`, error)
    } finally {
      loading.value = false
    }
  }

  /**
   * Toggle expanded state or fetch if not available
   */
  function toggle(summaryEffort) {
    if (isAvailable.value) {
      expanded.value = !expanded.value
    } else {
      fetch(summaryEffort)
    }
  }

  /**
   * Collapse the summary/tldr
   */
  function collapse() {
    expanded.value = false
  }

  /**
   * Expand the summary/tldr
   */
  function expand() {
    expanded.value = true
  }

  return {
    // State
    data,
    status,
    markdown,
    html,
    errorMessage,
    loading: isLoading,
    expanded,
    effort,

    // Computed
    isAvailable,
    isError,
    buttonLabel,

    // Methods
    fetch,
    toggle,
    collapse,
    expand
  }
}
