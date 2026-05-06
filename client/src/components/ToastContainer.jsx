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
        toast-liquid group relative w-full max-w-[min(34rem,calc(100vw-1.5rem))] overflow-hidden
        rounded-[28px] border border-white/70 bg-white/[0.72] px-4 py-3.5 text-left text-slate-900
        shadow-[0_22px_70px_-30px_rgba(14,46,72,0.55),0_10px_28px_-20px_rgba(14,165,233,0.55),inset_0_1px_0_rgba(255,255,255,0.95)]
        ring-1 ring-brand-200/[0.45] backdrop-blur-2xl
        pointer-events-auto cursor-pointer transition-[transform,box-shadow,border-color] duration-300 ease-[var(--ease-springy)]
        hover:-translate-y-0.5 hover:border-brand-100 hover:shadow-[0_26px_78px_-30px_rgba(14,46,72,0.62),0_12px_34px_-19px_rgba(14,165,233,0.65),inset_0_1px_0_rgba(255,255,255,1)]
        focus:outline-none focus:ring-2 focus:ring-brand-300/80 active:translate-y-0
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
      aria-label={`Open summary for ${title}`}
      aria-live="polite"
    >
      <span className="pointer-events-none absolute -left-10 top-1/2 h-28 w-28 -translate-y-1/2 rounded-full bg-brand-200/[0.35] blur-3xl" />
      <span className="pointer-events-none absolute -right-12 -top-16 h-32 w-40 rounded-full bg-white/80 blur-2xl" />
      <span className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />
      <span className="relative flex items-center gap-3.5">
        <span className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-brand-50/80 text-brand-700 ring-1 ring-brand-200/55 shadow-[inset_0_1px_0_rgba(255,255,255,0.95),0_10px_24px_-18px_rgba(2,132,199,0.9)] backdrop-blur-xl">
          <span className="absolute inset-1 rounded-full bg-gradient-to-br from-white/90 via-brand-50/25 to-brand-100/60" />
          <CheckCircle2 size={25} strokeWidth={1.9} className="relative" />
        </span>
        <span className="min-w-0 flex-1 pt-0.5">
          <span className="block text-[12px] font-bold uppercase tracking-[0.32em] text-brand-700/90">
            Summary ready
          </span>
          <span className="mt-1 block truncate font-display text-[23px] font-bold leading-[1.05] tracking-[-0.04em] text-slate-950 sm:text-[24px]">
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
    <div className="fixed left-0 right-0 top-4 z-[300] flex flex-col items-center gap-2.5 px-3 pointer-events-none sm:px-4">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
