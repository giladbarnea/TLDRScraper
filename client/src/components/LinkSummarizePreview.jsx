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
import { AlignLeft, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { markdownToHtml } from '../lib/markdownUtils'
import { overlayProseClassName } from './BaseOverlay'

function UrlEcho({ url }) {
  if (!url) return null
  const truncated = url.length > 80 ? `${url.slice(0, 80)}…` : url
  return (
    <p className="text-xs font-mono text-slate-500 leading-snug line-clamp-1 break-all">
      {truncated}
    </p>
  )
}

function LoadingBody({ url }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-6 text-center">
      <motion.div
        animate={{ scale: [1, 1.08, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-500"
      >
        <AlignLeft size={22} />
      </motion.div>
      <p className="text-sm font-medium text-slate-500">Summarizing…</p>
      <div className="max-w-sm">
        <UrlEcho url={url} />
      </div>
    </div>
  )
}

function ErrorBody({ message }) {
  return (
    <div className="flex flex-1 items-center justify-center px-6">
      <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600">
        {message || 'Summarization failed. Try again.'}
      </p>
    </div>
  )
}

function AvailableBody({ markdown, url }) {
  const html = useMemo(() => markdownToHtml(markdown), [markdown])
  return (
    <>
      <div className="shrink-0 border-b border-slate-200/60 px-5 py-3">
        <UrlEcho url={url} />
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </>
  )
}

function LinkSummarizePreview({ isOpen, status, url, markdown, errorMessage, onClose }) {
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
  const dismiss = useDismiss(context, { escapeKey: true, outsidePress: true })
  const { getFloatingProps } = useInteractions([dismiss])

  if (!isMounted) return null

  return (
    <FloatingNode id={nodeId}>
      <FloatingPortal>
        <AnimatePresence onExitComplete={() => setIsMounted(false)}>
          {isOpen && (
            <motion.div
              className="fixed inset-0 z-[210] flex items-center justify-center"
              onClick={(event) => event.stopPropagation()}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              <div className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm" />
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
                    'aria-label': 'Link Summary',
                    initial: { opacity: 0, scale: 0.92 },
                    animate: { opacity: 1, scale: 1 },
                    exit: { opacity: 0, scale: 0.96 },
                    transition: { type: 'spring', stiffness: 320, damping: 28 },
                    className: 'relative flex h-[60vh] w-[85vw] max-w-xl flex-col overflow-hidden rounded-3xl border border-white/60 bg-white/80 shadow-elevated backdrop-blur-2xl',
                  })}
                >
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent" />

                  <button
                    ref={closeButtonRef}
                    type="button"
                    onClick={onClose}
                    aria-label="Close"
                    className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white/70 text-slate-500 shadow-card backdrop-blur transition-colors hover:bg-white hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-400/60"
                  >
                    <X size={15} />
                  </button>

                  {status === 'loading' && <LoadingBody url={url} />}
                  {status === 'error' && <ErrorBody message={errorMessage} />}
                  {status === 'available' && <AvailableBody markdown={markdown} url={url} />}
                </motion.div>
              </FloatingFocusManager>
            </motion.div>
          )}
        </AnimatePresence>
      </FloatingPortal>
    </FloatingNode>
  )
}

export default LinkSummarizePreview
