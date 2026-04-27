import { AnimatePresence, motion } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import { useEffect } from 'react'
import { createPortal } from 'react-dom'
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
  const html = markdownToHtml(markdown)
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
  useEffect(() => {
    if (!isOpen) return
    function handleKeyDown(event) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      event.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', handleKeyDown, true)
    return () => document.removeEventListener('keydown', handleKeyDown, true)
  }, [isOpen, onClose])

  return createPortal(
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-[210] flex items-center justify-center"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <button
            type="button"
            aria-label="Dismiss elaboration"
            className="absolute inset-0 bg-slate-900/30 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Elaboration"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
            className="relative flex h-[60vh] w-[85vw] max-w-xl flex-col overflow-hidden rounded-3xl border border-white/60 bg-white/80 shadow-elevated backdrop-blur-2xl"
          >
            <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/80 to-transparent" />

            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-white/70 text-slate-500 shadow-card backdrop-blur transition-colors hover:bg-white hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-400/60"
            >
              <X size={15} />
            </button>

            {status === 'loading' && <LoadingBody selectedText={selectedText} />}
            {status === 'error' && <ErrorBody message={errorMessage} />}
            {status === 'available' && (
              <AvailableBody markdown={markdown} selectedText={selectedText} />
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}

export default ElaborationPreview
