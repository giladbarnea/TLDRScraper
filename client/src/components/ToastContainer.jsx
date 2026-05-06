import { CheckCircle2 } from 'lucide-react'
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
    <button
      type="button"
      onClick={handleClick}
      className={`
        relative w-full max-w-[min(26rem,calc(100vw-2rem))] overflow-hidden rounded-2xl
        border border-slate-200/70 bg-white/88 px-3.5 py-3 text-left text-slate-900
        shadow-[0_14px_40px_-28px_rgba(15,23,42,0.55),0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.94)]
        backdrop-blur-xl
        pointer-events-auto cursor-pointer transition-[transform,box-shadow,border-color,background-color] duration-200 ease-[var(--ease-springy)]
        hover:-translate-y-px hover:border-slate-300/80 hover:bg-white/94 hover:shadow-[0_16px_44px_-26px_rgba(15,23,42,0.6),0_1px_2px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.98)]
        focus:outline-none focus:ring-2 focus:ring-slate-300/80 active:translate-y-0
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
      aria-label={`Open summary for ${title}`}
      aria-live="polite"
    >
      <span className="pointer-events-none absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />
      <span className="flex items-center gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-slate-200/70 bg-slate-50/80 text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.95)]">
          <CheckCircle2 size={20} strokeWidth={1.8} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[12px] font-medium leading-none text-slate-500">
            Summary ready
          </span>
          <span className="mt-1 block truncate text-[15px] font-semibold leading-tight tracking-[-0.01em] text-slate-950">
            {title}
          </span>
        </span>
      </span>
    </button>
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
    <div className="fixed left-0 right-0 top-3 z-[300] flex flex-col items-center gap-2 px-4 pointer-events-none">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
