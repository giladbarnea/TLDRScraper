import { ChevronDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { usePullToClose } from '../hooks/usePullToClose'
import { useScrollProgress } from '../hooks/useScrollProgress'

function ZenOverlayShell({
  children,
  onClose,
  headerCenter,
  headerRight,
  includeProgressBar = true,
  portalZIndexClass = 'z-[100]',
  scrollRef: providedScrollRef
}) {
  const [hasScrolled, setHasScrolled] = useState(false)
  const containerRef = useRef(null)
  const internalScrollRef = useRef(null)
  const scrollRef = providedScrollRef || internalScrollRef
  const progress = useScrollProgress(scrollRef)
  const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose })

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    const handleEscape = (event) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)

    const scrollElement = scrollRef.current
    const handleScroll = () => {
      setHasScrolled(scrollElement.scrollTop > 10)
    }
    scrollElement?.addEventListener('scroll', handleScroll, { passive: true })

    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
      scrollElement?.removeEventListener('scroll', handleScroll)
    }
  }, [onClose])

  return createPortal(
    <div
      className={`fixed inset-0 ${portalZIndexClass}`}
      style={{
        transform: `translateY(${pullOffset}px)`,
        transition: pullOffset === 0 ? 'transform 0.3s ease-out' : 'none'
      }}
    >
      <div ref={containerRef} className="w-full h-full bg-white flex flex-col animate-zen-enter">
        <div
          className={`
            relative shrink-0 z-10
            flex items-center justify-between px-4 py-3
            transition-all duration-200
            ${hasScrolled ? 'bg-white/80 backdrop-blur-md border-b border-slate-200/60' : 'bg-white'}
          `}
        >
          <button
            onClick={onClose}
            className="shrink-0 p-2 rounded-full hover:bg-slate-200/80 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ChevronDown size={20} />
          </button>

          <div className="min-w-0 flex-1 px-2 flex justify-center">{headerCenter}</div>

          <div className="shrink-0">{headerRight}</div>

          {includeProgressBar && (
            <div
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 origin-left transition-transform duration-100"
              style={{ transform: `scaleX(${progress})` }}
            />
          )}
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto bg-white">
          {children({ scrollRef })}
        </div>
      </div>
    </div>,
    document.body
  )
}

export default ZenOverlayShell
