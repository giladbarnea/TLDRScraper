import { Check, CheckCircle, ChevronDown } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useOverscrollUp } from '../hooks/useOverscrollUp'
import { usePullToClose } from '../hooks/usePullToClose'
import { useScrollProgress } from '../hooks/useScrollProgress'

const OVERLAY_OVERSCROLL_THRESHOLD = 60
const OVERLAY_CONTENT_SHIFT_FACTOR = 0.4

export const overlayProseClassName = 'prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900 prose-headings:tracking-tight prose-h1:text-2xl prose-h1:font-bold prose-h2:text-xl prose-h2:font-semibold prose-h3:text-lg prose-h3:font-semibold prose-blockquote:border-slate-200 prose-strong:text-slate-900 [&]:[-webkit-touch-callout:none]'

function BaseOverlay({
  expanded = true,
  headerContent,
  onClose,
  onMarkRemoved,
  onContentContextMenu,
  children,
}) {
  const containerRef = useRef(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (!expanded) return
    const el = scrollRef.current
    if (!el) return

    let touchInfo = null
    const LONG_PRESS_MS = 500
    const MOVE_TOLERANCE = 20

    function handleTouchStart(event) {
      const touch = event.touches[0]
      touchInfo = { time: Date.now(), x: touch.clientX, y: touch.clientY }
      console.log('[longpress] touchstart at', touch.clientX.toFixed(0), touch.clientY.toFixed(0))
    }

    function handleTouchMove(event) {
      if (!touchInfo) return
      const touch = event.touches[0]
      const dx = Math.abs(touch.clientX - touchInfo.x)
      const dy = Math.abs(touch.clientY - touchInfo.y)
      if (dx > MOVE_TOLERANCE || dy > MOVE_TOLERANCE) {
        console.log('[longpress] cancelled — moved', dx.toFixed(0), dy.toFixed(0))
        touchInfo = null
      }
    }

    function handleTouchEnd(event) {
      if (!touchInfo) {
        console.log('[longpress] touchend — no active tracking')
        return
      }
      const elapsed = Date.now() - touchInfo.time
      const touch = event.changedTouches[0]
      console.log('[longpress] touchend — elapsed:', elapsed, 'ms')

      if (elapsed >= LONG_PRESS_MS) {
        console.log('[longpress] ✓ detected, dispatching contextmenu at', touch.clientX.toFixed(0), touch.clientY.toFixed(0))
        event.target.dispatchEvent(new MouseEvent('contextmenu', {
          bubbles: true,
          cancelable: true,
          clientX: touch.clientX,
          clientY: touch.clientY,
        }))
      }
      touchInfo = null
    }

    function handleTouchCancel() {
      console.log('[longpress] touchcancel — iOS hijacked')
      touchInfo = null
    }

    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: true })
    el.addEventListener('touchend', handleTouchEnd, { passive: true })
    el.addEventListener('touchcancel', handleTouchCancel, { passive: true })

    return () => {
      el.removeEventListener('touchstart', handleTouchStart)
      el.removeEventListener('touchmove', handleTouchMove)
      el.removeEventListener('touchend', handleTouchEnd)
      el.removeEventListener('touchcancel', handleTouchCancel)
    }
  }, [expanded])

  const { progress, hasScrolled } = useScrollProgress(scrollRef, expanded)
  const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose, enabled: false })
  const {
    overscrollOffset,
    isOverscrolling,
    progress: overscrollProgress,
    isComplete: overscrollComplete,
  } = useOverscrollUp({
    scrollRef,
    onComplete: onMarkRemoved,
    threshold: OVERLAY_OVERSCROLL_THRESHOLD,
    enabled: expanded,
  })

  useEffect(() => {
    if (!expanded) return

    document.body.style.overflow = 'hidden'

    function handleEscape(event) {
      if (event.key !== 'Escape') return
      if (event.defaultPrevented) return

      onClose()
    }

    document.addEventListener('keydown', handleEscape)

    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
    }
  }, [expanded, onClose])

  if (!expanded) return null

  return createPortal(
    <div
      onClick={(e) => e.stopPropagation()}
      className="fixed inset-0 z-[100]"
      style={{
        transform: `translateY(${pullOffset}px)`,
        transition: pullOffset === 0 ? 'transform 0.3s ease-out' : 'none',
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

          {headerContent}

          <button
            onClick={onMarkRemoved}
            className="shrink-0 p-2 rounded-full hover:bg-green-100 text-slate-500 hover:text-green-600 transition-colors"
          >
            <Check size={20} />
          </button>

          <div
            className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand-500 origin-left transition-transform duration-100"
            style={{ transform: `scaleX(${progress})` }}
          />
        </div>

        <div
          ref={scrollRef}
          onContextMenu={onContentContextMenu}
          onPointerDown={(e) => console.log('[overlay] pointerdown | type:', e.pointerType)}
          className="flex-1 overflow-y-auto bg-white coarse:select-none"
        >
          <div
            className="px-6 pt-2 pb-5 md:px-8 md:pt-3 md:pb-6"
            style={{
              transform: `translateY(-${overscrollOffset * OVERLAY_CONTENT_SHIFT_FACTOR}px)`,
              transition: isOverscrolling ? 'none' : 'transform 0.2s ease-out',
            }}
          >
            <div className="max-w-3xl mx-auto">{children}</div>
          </div>

          <div
            className={`
              flex items-center justify-center py-16 transition-all duration-150
              ${isOverscrolling ? 'opacity-100' : 'opacity-0'}
            `}
            style={{ transform: `translateY(${isOverscrolling ? 0 : 20}px)` }}
          >
            <div
              className={`
                w-12 h-12 rounded-full flex items-center justify-center transition-all duration-150
                ${overscrollComplete ? 'bg-green-500 text-white scale-110' : 'bg-slate-100 text-slate-400'}
              `}
            >
              <CheckCircle
                size={24}
                style={{
                  opacity: 0.3 + overscrollProgress * 0.7,
                  transform: `scale(${0.8 + overscrollProgress * 0.2})`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

export default BaseOverlay
