import { motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useInteraction } from '../contexts/InteractionContext'
import { useArticleState } from '../hooks/useArticleState'
import { usePullToClose } from '../hooks/usePullToClose'
import { useSummary } from '../hooks/useSummary'
import { useSwipeToRemove } from '../hooks/useSwipeToRemove'
import Selectable from './Selectable'

function ErrorToast({ message, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000)
    return () => clearTimeout(timer)
  }, [onDismiss])

  return createPortal(
    <div className="fixed bottom-4 left-4 right-4 z-[200] bg-red-600 text-white p-4 rounded-xl shadow-lg flex items-start gap-3">
      <AlertCircle size={20} className="shrink-0 mt-0.5" />
      <div className="flex-1 text-sm font-medium break-all">{message}</div>
      <button onClick={onDismiss} className="shrink-0 text-white/80 hover:text-white">✕</button>
    </div>,
    document.body
  )
}

function ZenModeOverlay({ html, hostname, displayDomain, title, onClose, onMarkRemoved }) {
  const containerRef = useRef(null)
  const scrollRef = useRef(null)
  const { pullOffset } = usePullToClose({ containerRef, scrollRef, onClose })

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])

  return createPortal(
    <motion.div
      initial={{ opacity: 0, y: 100 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 100 }}
      transition={{ type: "spring", damping: 25, stiffness: 200 }}
      className="fixed inset-0 z-50 bg-white flex flex-col"
      style={{
        transform: `translateY(${pullOffset}px)`,
        transition: pullOffset === 0 ? 'transform 0.3s ease-out' : 'none'
      }}
    >
      <div className="sticky top-0 bg-white/90 backdrop-blur-md border-b border-gray-100 px-6 py-4 flex items-center justify-between z-10">
        <span className="text-xs font-bold uppercase tracking-widest text-gray-400">
          Reading Mode
        </span>
        <button
          onClick={onClose}
          className="p-2 -mr-2 text-gray-400 hover:text-gray-900 transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto bg-white">
        <div ref={scrollRef} className="max-w-xl mx-auto px-6 py-12">
          <h1 className="font-sans font-bold text-3xl text-gray-900 leading-tight mb-4">
            {title}
          </h1>
          <div className="flex items-center gap-2 mb-10 text-sm text-gray-500 font-medium">
            {hostname && (
              <img
                src={`https://www.google.com/s2/favicons?domain=${hostname}`}
                alt=""
                className="w-4 h-4 opacity-70"
              />
            )}
            {displayDomain}
          </div>

          <div
            className="zen-content prose prose-lg prose-gray font-serif text-gray-800"
            dangerouslySetInnerHTML={{ __html: html }}
          />

          <div className="h-32 flex items-center justify-center mt-12 border-t border-gray-100">
            <button onClick={onMarkRemoved} className="flex flex-col items-center gap-2 text-gray-400 hover:text-green-600 transition-colors">
              <div className="w-12 h-12 rounded-full border-2 border-current flex items-center justify-center">
                <Check size={24} />
              </div>
              <span className="text-xs font-sans font-bold uppercase tracking-widest">Mark Done</span>
            </button>
          </div>
        </div>
      </div>
    </motion.div>,
    document.body
  )
}

function MetaRow({ domain }) {
  return (
    <div className="flex items-center gap-2 mb-1.5">
      <span className="text-meta text-[10px] text-ink-500 bg-gray-50 px-1.5 py-0.5 rounded border border-gray-100">
        {domain}
      </span>
      <span className="text-[10px] text-ink-500">•</span>
      <span className="text-[10px] text-ink-500 font-medium">
        TODAY
      </span>
    </div>
  )
}

function ArticleTitle({ title, isRead }) {
  return (
    <h3 className={`text-base font-semibold leading-snug transition-colors ${
      isRead ? 'text-ink-500 line-through decoration-ink-200' : 'text-ink-900'
    }`}>
      {title}
    </h3>
  )
}

function ArticleCard({ article }) {
  const { isSelectMode, registerDisabled, itemShortPress } = useInteraction()
  const { isRead, isRemoved, toggleRemove, markAsRemoved, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )
  const summary = useSummary(article.issueDate, article.url)

  const componentId = `article-${article.url}`

  const handleSwipeComplete = () => {
    if (!isRemoved && summary.expanded) summary.collapse()
    toggleRemove()
  }

  const { dragError, clearDragError, canDrag, handleDragStart } = useSwipeToRemove({
    isRemoved,
    stateLoading,
    onSwipeComplete: handleSwipeComplete,
    url: article.url,
  })

  const swipeEnabled = canDrag && !isSelectMode

  const fullUrl = article.url.startsWith('http://') || article.url.startsWith('https://')
    ? article.url
    : `https://${article.url}`

  const { displayDomain, hostname } = (() => {
    try {
      const urlObj = new URL(fullUrl)
      const h = urlObj.hostname
      const d = h.replace(/^www\./, '').split('.')[0].toLowerCase()
      return { displayDomain: d, hostname: h }
    } catch {
      return { displayDomain: null, hostname: null }
    }
  })()

  const handleCardClick = (e) => {
    if (isDragging) return

    if (isRemoved) {
      e.preventDefault()
      toggleRemove()
      return
    }

    const selection = window.getSelection()
    if (selection.toString().length > 0) return

    const shouldOpen = itemShortPress(componentId)
    if (shouldOpen) {
      summary.toggle()
    }
  }

  useEffect(() => {
    registerDisabled(componentId, isRemoved)
    return () => registerDisabled(componentId, false)
  }, [componentId, isRemoved, registerDisabled])

  return (
    <>
      <Selectable id={componentId} disabled={isRemoved}>
        <motion.div
          style={{ x: 0 }}
          onPan={swipeEnabled ? handleDragStart : undefined}
          layout
          className="group relative mb-3 last:mb-0"
        >
          <div
            onClick={handleCardClick}
            className={`
              card-base overflow-hidden relative cursor-pointer
              ${summary.expanded ? 'ring-1 ring-black/5 shadow-sm' : 'hover:border-gray-300'}
            `}
          >
            <div className="p-4">
              <MetaRow domain={displayDomain} />
              <ArticleTitle title={article.title} isRead={isRead} />
            </div>
          </div>
        </motion.div>
      </Selectable>

      {!isRemoved && summary.expanded && summary.html && (
        <ZenModeOverlay
          html={summary.html}
          hostname={hostname}
          displayDomain={displayDomain}
          title={article.title}
          onClose={() => summary.collapse()}
          onMarkRemoved={() => {
            summary.collapse(false)
            markAsRemoved()
          }}
        />
      )}

      {dragError && <ErrorToast message={dragError} onDismiss={clearDragError} />}
    </>
  )
}

export default ArticleCard
