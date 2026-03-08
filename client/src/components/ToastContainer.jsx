import { CheckCircle } from 'lucide-react'
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
        relative overflow-hidden
        flex items-center gap-3
        bg-gradient-to-r from-brand-50/95 to-white/95 text-slate-900
        px-4 py-3.5 rounded-2xl
        border border-brand-200/70
        ring-1 ring-brand-100/80
        shadow-elevated backdrop-blur-sm
        max-w-md w-full
        pointer-events-auto cursor-pointer
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
    >
      <span className="absolute inset-y-0 left-0 w-1.5 bg-brand-300/80" />
      <span className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
        <CheckCircle size={16} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-700/90">Summary ready</p>
        <p className="text-base font-semibold text-slate-800 truncate">{title}</p>
      </div>
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
    <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
