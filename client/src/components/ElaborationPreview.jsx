import {
  FloatingFocusManager,
  FloatingNode,
  FloatingPortal,
  useDismiss,
  useFloating,
  useFloatingNodeId,
  useInteractions,
} from '@floating-ui/react'
import { AnimatePresence, motion } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { markdownToHtml } from '../lib/markdownUtils'
import { overlayProseClassName } from './BaseOverlay'

function SnippetEcho({ text }) {
  if (!text) return null
  const truncated = text.length > 120 ? `${text.slice(0, 120)}…` : text
  return (
    <p className="text-xs font-serif italic text-slate-500 leading-snug line-clamp-2">
      “{truncated}”
    </p>
  )
}

function LoadingBody({ selectedText }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <motion.div
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500"
      >
        <Sparkles size={22} />
      </motion.div>
      <p className="text-sm font-medium text-slate-500">Elaborating…</p>
      <div className="max-w-sm">
        <SnippetEcho text={selectedText} />
      </div>
    </div>
  )
}

function ErrorBody({ message }) {
  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
        {message || 'Elaboration failed. Try again.'}
      </p>
    </div>
  )
}

function AvailableBody({ markdown, selectedText }) {
  const html = useMemo(() => markdownToHtml(markdown), [markdown])
  return (
    <>
      <div className="shrink-0 border-b border-slate-200/60 px-5 py-3">
        <SnippetEcho text={selectedText} />
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </>
  )
}

function ElaborationPreview({ isOpen, status, selectedText, markdown, errorMessage, onClose }) {
  const [isMounted, setIsMounted] = useState(isOpen)
  const closeButtonRef = useRef(null)
  const nodeId = useFloatingNodeId()

  useEffect(() => {
    if (isOpen) setIsMounted(true)
  }, [isOpen])

  const { refs, context } = useFloating({
    nodeId,
    open: isMounted,
    onOpenChange: (open) => {
      if (!open) onClose()
    },
  })
  const dismiss = useDismiss(context, {
    escapeKey: true,
    outsidePress: true,
  })
  const { getFloatingProps } = useInteractions([dismiss])

  if (!isMounted) return null

  return (
    <FloatingNode id={nodeId}>
      <FloatingPortal>
        <AnimatePresence onExitComplete={() => setIsMounted(false)}>
          {isOpen && (
            <motion.div
              className="fixed inset-0 z-[210] flex items-center justify-center px-4"
              onClick={(event) => event.stopPropagation()}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <div className="absolute inset-0 bg-slate-900/28 backdrop-blur-md" />
              <FloatingFocusManager
                context={context}
                modal={true}
                returnFocus={true}
                initialFocus={closeButtonRef}
              >
                <motion.div
                  {...getFloatingProps({
                    ref: refs.setFloating,
                    role: 'dialog',
                    'aria-modal': true,
                    'aria-label': 'Elaboration',
                    initial: { opacity: 0, scale: 0.92 },
                    animate: { opacity: 1, scale: 1 },
                    exit: { opacity: 0, scale: 0.96 },
                    transition: { type: 'spring', stiffness: 320, damping: 28 },
                    className: 'relative flex h-[60vh] w-full max-w-xl flex-col overflow-hidden rounded-[32px] border border-white/70 bg-white/[0.78] shadow-[0_30px_90px_-38px_rgba(15,23,42,0.48),0_1px_2px_rgba(15,23,42,0.04),inset_0_1px_0_rgba(255,255,255,0.96)] ring-1 ring-slate-200/60 backdrop-blur-2xl',
                  })}
                >
                  <div className="pointer-events-none absolute -right-20 -top-24 h-48 w-56 rounded-full bg-white/75 blur-3xl" />
                  <div className="pointer-events-none absolute -left-24 top-10 h-48 w-48 rounded-full bg-slate-200/40 blur-3xl" />
                  <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent" />

                  <button
                    ref={closeButtonRef}
                    type="button"
                    onClick={onClose}
                    aria-label="Close"
                    className="absolute right-3 top-3 z-10 flex h-11 w-11 items-center justify-center rounded-full border border-white/70 bg-white/[0.58] text-slate-600 shadow-[0_12px_24px_-18px_rgba(15,23,42,0.75),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-xl transition-[background-color,color,transform] duration-200 hover:-translate-y-0.5 hover:bg-white/[0.82] hover:text-slate-950 focus:outline-none focus:ring-2 focus:ring-slate-300/80"
                  >
                    <X size={15} />
                  </button>

                  {status === 'loading' && <LoadingBody selectedText={selectedText} />}
                  {status === 'error' && <ErrorBody message={errorMessage} />}
                  {status === 'available' && (
                    <AvailableBody markdown={markdown} selectedText={selectedText} />
                  )}
                </motion.div>
              </FloatingFocusManager>
            </motion.div>
          )}
        </AnimatePresence>
      </FloatingPortal>
    </FloatingNode>
  )
}

export default ElaborationPreview
