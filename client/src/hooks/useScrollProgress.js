import { useEffect, useState } from 'react'

const HAS_SCROLLED_THRESHOLD = 10

export function useScrollProgress(scrollRef, enabled = true) {
  const [progress, setProgress] = useState(0)
  const [hasScrolled, setHasScrolled] = useState(false)

  useEffect(() => {
    if (!enabled) {
      setProgress(0)
      setHasScrolled(false)
      return
    }

    const element = scrollRef.current
    if (!element) return

    function updateProgress() {
      const { scrollTop, scrollHeight, clientHeight } = element
      const maxScroll = scrollHeight - clientHeight
      const currentProgress = maxScroll > 0 ? scrollTop / maxScroll : 0
      setProgress(Math.min(1, Math.max(0, currentProgress)))
      setHasScrolled(scrollTop > HAS_SCROLLED_THRESHOLD)
    }

    updateProgress()
    element.addEventListener('scroll', updateProgress, { passive: true })
    return () => element.removeEventListener('scroll', updateProgress)
  }, [enabled, scrollRef])

  return { progress, hasScrolled }
}
