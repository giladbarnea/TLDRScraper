import { CheckCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { subscribeToToasts } from '../lib/toastBus'

const TOAST_VISIBLE_MS = 4000
const EXIT_ANIMATION_MS = 220

function Toast({ id, title, onDismiss }) {
  const [exiting, setExiting] = useState(false)

  useEffect(() => {
    const exitTimer = setTimeout(() => setExiting(true), TOAST_VISIBLE_MS - EXIT_ANIMATION_MS)
    const removeTimer = setTimeout(() => onDismiss(id), TOAST_VISIBLE_MS)
    return () => {
      clearTimeout(exitTimer)
      clearTimeout(removeTimer)
    }
  }, [id, onDismiss])

  return (
    <div
      className={`
        flex items-center gap-2.5
        bg-slate-800 text-white
        px-4 py-2.5 rounded-2xl
        shadow-elevated
        max-w-sm w-full
        ${exiting ? 'animate-toast-out' : 'animate-toast-in'}
      `}
    >
      <CheckCircle size={15} className="text-brand-400 shrink-0" />
      <span className="text-sm font-medium text-white/90 truncate">
        {title ? `Summary ready — ${title}` : 'Summary ready'}
      </span>
    </div>
  )
}

export default function ToastContainer() {
  const [toasts, setToasts] = useState([])

  useEffect(() => subscribeToToasts((toast) => {
    setToasts(prev => [...prev, { ...toast, id: `${Date.now()}-${Math.random().toString(16).slice(2)}` }])
  }), [])

  const dismiss = (id) => setToasts(prev => prev.filter(t => t.id !== id))

  if (toasts.length === 0) return null

  return createPortal(
    <div className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2 pointer-events-none px-4">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>,
    document.body
  )
}
