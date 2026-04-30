import { Toast } from '@base-ui/react/toast'
import { CheckCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { subscribeToToasts } from '../lib/toastBus'

const TOAST_VISIBLE_MS = 12000

function ToastItem({ id, title, onOpen, onDismiss }) {
  return (
    <Toast.Root
      defaultOpen
      onOpenChange={(open) => {
        if (!open) onDismiss(id)
      }}
      className="group pointer-events-auto max-w-md w-full"
    >
      <Toast.Close className="sr-only">Dismiss toast</Toast.Close>
      <Toast.Description
        onClick={() => {
          onOpen?.()
          onDismiss(id)
        }}
        className="
          relative overflow-hidden
          flex items-center gap-3
          bg-gradient-to-r from-brand-50/95 to-white/95 text-slate-900
          px-4 py-3.5 rounded-2xl
          border border-brand-200/70
          ring-1 ring-brand-100/80
          shadow-elevated backdrop-blur-sm
          cursor-pointer
          animate-toast-in
          data-[ending-style]:animate-toast-out
        "
      >
        <span className="absolute inset-y-0 left-0 w-1.5 bg-brand-300/80" />
        <span className="ml-2 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-700">
          <CheckCircle size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-brand-700/90">Summary ready</p>
          <p className="text-base font-semibold text-slate-800 truncate">{title}</p>
        </div>
      </Toast.Description>
    </Toast.Root>
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

  if (toasts.length === 0) return null

  return (
    <Toast.Provider timeout={TOAST_VISIBLE_MS}>
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          {...toast}
          onDismiss={(id) => setToasts(previousToasts => previousToasts.filter((item) => item.id !== id))}
        />
      ))}
      <Toast.Viewport className="fixed top-4 left-0 right-0 z-[300] flex flex-col items-center gap-2.5 pointer-events-none px-4" />
    </Toast.Provider>
  )
}
