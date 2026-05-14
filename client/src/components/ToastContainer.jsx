import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'

const TOAST_VISIBLE_MS = 12000
const EXIT_ANIMATION_MS = 350

function Toast({ id, title, onOpen, onDismiss, persistent = false }) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    if (persistent) return
    const exitTimer = setTimeout(() => setExiting(true), TOAST_VISIBLE_MS - EXIT_ANIMATION_MS)
    const removeTimer = setTimeout(() => onDismiss(id), TOAST_VISIBLE_MS)
    return () => {
      clearTimeout(exitTimer)
      clearTimeout(removeTimer)
    }
  }, [id, onDismiss, persistent])

  const handleClick = () => {
    onOpen?.()
    onDismiss(id)
  }

  return (
    <div
      onClick={handleClick}
      className={`
        liquid-glass-toast
        relative
        px-6 py-3.5 rounded-[22px]
        max-w-md w-full
        pointer-events-auto cursor-pointer
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
    >
      <p
        className="font-display text-[17px] font-semibold text-black truncate"
        style={{ letterSpacing: '-0.015em' }}
      >
        {title}
      </p>
    </div>
  )
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => subscribeToToasts((toast) => {
    setToasts(previousToasts => {
      const nextToast = { ...toast, id: `${Date.now()}-${Math.random().toString(16).slice(2)}` }
      return [...previousToasts, nextToast].slice(-2)
    })
  }), [])

  const dismiss = useCallback((id) => setToasts(prev => prev.filter(t => t.id !== id)), [])

  return createPortal(
    <>
      <LiquidGlassFilter />
      <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4">
        <Toast id="mock" title="AI models now reason better than most humans on complex tasks" onDismiss={() => {}} persistent />
        {toasts.map(toast => (
          <Toast key={toast.id} {...toast} onDismiss={dismiss} />
        ))}
      </div>
    </>,
    document.body
  )
}

/* Refraction via self-referential displacement: the backdrop displaces itself.
 * R channel drives X displacement, B channel drives Y. Content edges (where
 * R/B change steeply, e.g. dark text on white) generate the strongest
 * displacement gradients, so text underneath the toast gets visibly warped
 * across the entire element body — not just at the perimeter. This is the
 * apple-liquid-glass-experiments technique. A mild post-displacement blur
 * smooths the warped result so it reads as fluid refraction.
 *
 * Chrome/Firefox only; Safari silently no-ops `backdrop-filter: url()`,
 * falling through to the box-shadow specular stack. */
function LiquidGlassFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" style={{ position: 'absolute' }}>
      <filter id="liquid-glass-lens" x="-10%" y="-10%" width="120%" height="120%" color-interpolation-filters="linearRGB">
        <feDisplacementMap in="SourceGraphic" in2="SourceGraphic" scale="40" xChannelSelector="R" yChannelSelector="B" result="displaced" />
        <feGaussianBlur in="displaced" stdDeviation="1.5" />
      </filter>
    </svg>
  )
}
