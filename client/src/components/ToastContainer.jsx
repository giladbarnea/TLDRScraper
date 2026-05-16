import { useCallback, useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'
import LiquidGlassSurface from './visual-effects/LiquidGlassSurface'
import LiquidGlassTouchLight from './visual-effects/LiquidGlassTouchLight'

const TOAST_VISIBLE_MS = 12000
const EXIT_ANIMATION_MS = 350
const MOCK_TOAST = {
  id: 'mock-liquid-glass-toast',
  title: 'Mock Liquid Glass toast',
  persistent: true,
}

function Toast({ id, title, onOpen, onDismiss, persistent = false }) {
  const [exiting, setExiting] = useState(false)
  const dismissTimerRef = useRef(null)

  useEffect(() => {
    if (persistent) return undefined
    const exitTimer = setTimeout(() => setExiting(true), TOAST_VISIBLE_MS - EXIT_ANIMATION_MS)
    const removeTimer = setTimeout(() => onDismiss(id), TOAST_VISIBLE_MS)
    return () => {
      clearTimeout(exitTimer)
      clearTimeout(removeTimer)
      if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current)
    }
  }, [id, onDismiss, persistent])

  const handleClick = () => {
    console.log('[Toast] click', { id, persistent, exiting })
    if (persistent || exiting) return
    onOpen?.()
    setExiting(true)
    dismissTimerRef.current = setTimeout(() => onDismiss(id), EXIT_ANIMATION_MS)
  }

  return (
    <LiquidGlassSurface
      variant="solid"
      depth="compact"
      lens="subtle"
      onClick={handleClick}
      className={[
        'relative flex min-h-[84px] max-w-md w-full items-center cursor-pointer pointer-events-auto rounded-[22px] px-6 py-[21px] overflow-hidden',
        persistent || !exiting ? 'animate-toast-in' : 'animate-toast-out',
      ].join(' ')}
    >
      <LiquidGlassTouchLight />
      <p
        className="relative font-display text-[17px] font-semibold text-black truncate"
        style={{ letterSpacing: '-0.015em', zIndex: 1 }}
      >
        {title}
      </p>
    </LiquidGlassSurface>
  )
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    return subscribeToToasts((toast) => {
      setToasts(previousToasts => {
        const nextToast = { ...toast, id: `${Date.now()}-${Math.random().toString(16).slice(2)}` }
        return [...previousToasts, nextToast].slice(-2)
      })
    })
  }, [])

  const dismiss = useCallback((id) => setToasts(previousToasts => previousToasts.filter(toast => toast.id !== id)), [])

  return createPortal(
    <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4">
      <Toast {...MOCK_TOAST} onDismiss={dismiss} />
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
