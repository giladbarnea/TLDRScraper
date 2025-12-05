import { useEffect, useState } from 'react'

export function useScrollProgress(scrollRef) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    const updateProgress = () => {
      const { scrollTop, scrollHeight, clientHeight } = element
      const maxScroll = scrollHeight - clientHeight
      const currentProgress = maxScroll > 0 ? scrollTop / maxScroll : 0
      setProgress(Math.min(1, Math.max(0, currentProgress)))
    }

    updateProgress()
    element.addEventListener('scroll', updateProgress, { passive: true })
    return () => element.removeEventListener('scroll', updateProgress)
  }, [scrollRef])

  return progress
}
