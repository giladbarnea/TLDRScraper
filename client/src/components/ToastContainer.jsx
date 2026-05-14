import { useCallback, useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'

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
    <div
      onClick={handleClick}
      className={`
        liquid-glass-toast
        relative
        text-slate-900
        px-5 py-3 rounded-[22px]
        max-w-md w-full
        pointer-events-auto cursor-pointer
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
    >
      <p className="text-[15px] font-semibold text-slate-900 truncate">{title}</p>
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

  if (toasts.length === 0) return null

  return createPortal(
    <>
      <LiquidGlassFilter />
      <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4">
        {toasts.map(toast => (
          <Toast key={toast.id} {...toast} onDismiss={dismiss} />
        ))}
      </div>
    </>,
    document.body
  )
}

/* feDisplacementMap with a radial normal map: zero displacement at the center,
 * maximum at the rim — bends content underneath the glass at the perimeter,
 * which is what reads as "refraction through curved glass." Chrome/Firefox
 * only; Safari silently no-ops `backdrop-filter: url()`, falling through to
 * the box-shadow specular stack defined in CSS. */
function LiquidGlassFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" style={{ position: 'absolute' }}>
      <filter id="liquid-glass-lens" x="-10%" y="-10%" width="120%" height="120%">
        <feImage
          x="0" y="0" result="normalMap"
          xlinkHref="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='400' height='80' preserveAspectRatio='none'><radialGradient id='m' cx='50%' cy='50%' r='80%'><stop offset='0%' stop-color='rgb(128,128,255)'/><stop offset='95%' stop-color='rgb(255,255,255)'/></radialGradient><rect width='100%' height='100%' fill='url(%23m)'/></svg>"
        />
        <feDisplacementMap in="SourceGraphic" in2="normalMap" scale="-60" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
  )
}
