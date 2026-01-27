import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { usePullToClose } from '../hooks/usePullToClose'

function BottomSheet({ isOpen, onClose, title, children }) {
  const containerRef = useRef(null)
  const scrollRef = useRef(null)
  const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose, threshold: 60 })

  useEffect(() => {
    if (!isOpen) return

    document.body.style.overflow = 'hidden'
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return createPortal(
    <div className="fixed inset-0 z-[100]">
      <div
        className="absolute inset-0 bg-black/40 animate-sheet-backdrop"
        onClick={onClose}
      />
      <div
        ref={containerRef}
        className="absolute bottom-0 left-0 right-0 h-[66vh] bg-white rounded-t-3xl animate-sheet-enter flex flex-col"
        style={{
          transform: `translateY(${pullOffset}px)`,
          transition: pullOffset === 0 ? 'transform 0.3s ease-out' : 'none'
        }}
      >
        <div className="flex items-center justify-center py-3">
          <div className="w-10 h-1 bg-slate-300 rounded-full" />
        </div>

        <div className="px-6 pb-4 border-b border-slate-100">
          <h2 className="text-lg font-display font-semibold text-slate-900 text-center">
            {title}
          </h2>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </div>,
    document.body
  )
}

export default BottomSheet
