import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'
import LiquidGlassSurface from './visual-effects/LiquidGlassSurface'
import LiquidGlassTouchLight from './visual-effects/LiquidGlassTouchLight'

const TOAST_VISIBLE_MS = 12000

function Toast({ id, title, onOpen, onDismiss }) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    const exitTimer = setTimeout(() => setExiting(true), TOAST_VISIBLE_MS)
    const removeTimer = setTimeout(() => onDismiss(id), TOAST_VISIBLE_MS + 350)
    return () => {
      clearTimeout(exitTimer)
      clearTimeout(removeTimer)
    }
  }, [id, onDismiss])

  const handleClick = () => {
    onOpen?.()
    onDismiss(id)
  }

  return (
    <LiquidGlassSurface
      variant="solid"
      depth="compact"
      lens="subtle"
      onClick={handleClick}
      className={[
        'relative flex min-h-[84px] max-w-md w-full items-center cursor-pointer pointer-events-auto rounded-[22px] px-6 py-[21px] overflow-hidden',
        exiting ? 'animate-toast-out' : 'animate-toast-in',
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

  if (toasts.length === 0) return null

  return createPortal(
    <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
