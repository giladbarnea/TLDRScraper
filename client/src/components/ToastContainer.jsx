import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'
import LiquidGlassSurface from './visual-effects/LiquidGlassSurface'

const TOAST_VISIBLE_MS = 12000
const EXIT_ANIMATION_MS = 350

function Toast({ id, title, onOpen, onDismiss }) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    const exitTimer = setTimeout(() => setExiting(true), TOAST_VISIBLE_MS - EXIT_ANIMATION_MS)
    const removeTimer = setTimeout(() => onDismiss(id), TOAST_VISIBLE_MS)
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
        'relative max-w-md w-full cursor-pointer pointer-events-auto rounded-[22px] px-6 py-3.5',
        exiting ? 'animate-toast-out' : 'animate-toast-in',
      ].join(' ')}
    >
      <p
        className="font-display text-[17px] font-semibold text-black truncate"
        style={{ letterSpacing: '-0.015em' }}
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
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
