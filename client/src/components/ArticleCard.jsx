import { CheckCircle, ChevronLeft, Loader2, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef } from 'react'
import { createPortal } from 'react-dom'
import { m, useAnimation, LazyMotion, domAnimation } from 'framer-motion'
import { useArticleState } from '../hooks/useArticleState'
import { useScrollProgress } from '../hooks/useScrollProgress'
import { useSummary } from '../hooks/useSummary'

function ZenModeOverlay({ title, html, onClose }) {
  const scrollRef = useRef(null)
  const progress = useScrollProgress(scrollRef)

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
    <div className="fixed inset-0 z-[100]">
      <div className="w-full h-full bg-white flex flex-col animate-zen-enter">
        <div className="flex items-center gap-3 p-5 border-b border-slate-100 bg-slate-50/80 shrink-0">
          <button
            onClick={onClose}
            className="shrink-0 p-2 rounded-full hover:bg-slate-200 text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ChevronLeft size={20} />
          </button>
          <h2 className="font-display font-semibold text-lg text-slate-800">
            {title}
          </h2>
        </div>
        <div
          className="h-0.5 bg-purple-500 origin-left transition-transform duration-100"
          style={{ transform: `scaleX(${progress})` }}
        />
        <div ref={scrollRef} className="overflow-y-auto flex-1 p-6 md:p-8 bg-white">
          <div className="max-w-3xl mx-auto">
            <div
              className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900"
              dangerouslySetInnerHTML={{ __html: html }}
            />
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

function ArticleTitle({ href, isRemoved, isRead, title, onLinkClick }) {
  return (
    <a
      href={isRemoved ? undefined : href}
      target={isRemoved ? undefined : "_blank"}
      rel={isRemoved ? undefined : "noopener noreferrer"}
      className={`
        text-[17px] font-display font-semibold leading-snug text-slate-900
        hover:text-brand-600 transition-colors duration-200 block tracking-tight
        ${isRead ? 'text-slate-500 font-normal' : ''}
        ${isRemoved ? 'pointer-events-none' : ''}
      `}
      onClick={onLinkClick}
    >
      {title}
    </a>
  )
}

function ArticleMeta({ domain, articleMeta, isRead, tldrLoading, onRemove, removeDisabled }) {
  return (
    <div className="mb-1 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-slate-400">
          {domain && domain}
          {domain && articleMeta && ' │ '}
          {articleMeta}
        </span>
        {isRead && <CheckCircle size={14} className="text-slate-300" />}
      </div>
      <div className="flex items-center gap-2">
        {tldrLoading && <Loader2 size={14} className="animate-spin text-brand-500" />}
        <button
          onClick={onRemove}
          disabled={removeDisabled}
          className={`p-1.5 rounded-full transition-colors ${removeDisabled ? 'text-slate-300 cursor-not-allowed' : 'text-slate-400 hover:text-red-500 hover:bg-red-50'}`}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

function TldrError({ message }) {
  return (
    <div className="mt-4 text-xs text-red-500 bg-red-50 p-3 rounded-lg">
      {message || 'Failed to load summary.'}
    </div>
  )
}

function ArticleCard({ article }) {
  const { isRead, isRemoved, toggleRead, toggleRemove, markTldrHidden, unmarkTldrHidden, loading: stateLoading } = useArticleState(
    article.issueDate,
    article.url
  )
  const tldr = useSummary(article.issueDate, article.url, 'tldr')
  const { isAvailable } = tldr

  const controls = useAnimation()

  const fullUrl = useMemo(() => {
    const url = article.url
    if (url.startsWith('http://') || url.startsWith('https://')) return url
    return `https://${url}`
  }, [article.url])

  const domain = useMemo(() => {
    try {
      const urlObj = new URL(fullUrl)
      const hostname = urlObj.hostname
      return hostname.replace(/^www\./, '').split('.')[0].toLowerCase()
    } catch {
      return null
    }
  }, [fullUrl])

  const toggleTldrWithTracking = (toggleFn) => {
    const wasExpanded = tldr.expanded
    toggleFn()

    if (wasExpanded) {
      markTldrHidden()
    } else {
      unmarkTldrHidden()
    }
  }

  const handleSwipeComplete = () => {
    if (!isRemoved && tldr.expanded) tldr.collapse()
    toggleRemove()
  }

  useEffect(() => {
    controls.start({
      opacity: stateLoading ? 0.4 : isRemoved ? 0.5 : 1,
      filter: stateLoading || isRemoved ? 'grayscale(100%)' : 'grayscale(0%)',
      scale: isRemoved ? 0.98 : 1,
      x: 0,
    })
  }, [isRemoved, stateLoading, controls])

  const handleDragEnd = async (event, { offset, velocity }) => {
    const swipeThreshold = -100
    const velocityThreshold = -300

    if (offset.x < swipeThreshold || velocity.x < velocityThreshold) {
      await controls.start({
        x: -window.innerWidth,
        opacity: 0,
        transition: { duration: 0.2, ease: "easeOut" }
      })
      handleSwipeComplete()
    } else {
      controls.start({ x: 0 })
    }
  }

  const handleCardClick = (e) => {
    if (isRemoved) {
      e.preventDefault()
      toggleRemove()
      return
    }

    const selection = window.getSelection()
    if (selection.toString().length > 0) return

    toggleTldrWithTracking(() => tldr.toggle())
  }

  return (
    <LazyMotion features={domAnimation}>
      <m.div
        layout
        className={`relative ${tldr.expanded && !stateLoading ? 'mb-6' : 'mb-3'}`}
      >
        <div className="absolute inset-0 rounded-[20px] bg-red-50 flex items-center justify-end pr-8">
          <Trash2 className="text-red-400" size={20} />
        </div>

        <m.div
          drag={!isRemoved && !stateLoading ? "x" : false}
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={{ left: 0.5, right: 0.1 }}
          animate={controls}
          initial={{ opacity: 1, filter: 'grayscale(0%)', scale: 1, x: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
          onDragEnd={handleDragEnd}
          whileHover={!isRemoved && !stateLoading ? { scale: 1.005 } : undefined}
          whileTap={!isRemoved && !stateLoading ? { scale: 0.99 } : undefined}
          onClick={handleCardClick}
          style={{ touchAction: "pan-y" }}
          data-article-title={article.title}
          data-article-url={article.url}
          data-article-date={article.issueDate}
          data-article-category={article.category}
          data-article-source={article.sourceId}
          data-read={isRead}
          data-removed={isRemoved}
          data-state-loading={stateLoading}
          data-tldr-status={tldr.status}
          data-tldr-expanded={tldr.expanded}
          data-tldr-available={isAvailable}
          className={`
            relative z-10
            rounded-[20px] border border-white/40
            shadow-[0_2px_12px_-4px_rgba(0,0,0,0.05)]
            backdrop-blur-xl
            cursor-pointer select-none
            ${isRemoved ? 'bg-slate-50' : 'bg-white'}
            ${stateLoading ? 'pointer-events-none' : ''}
            ${tldr.expanded && !stateLoading ? 'ring-1 ring-brand-100 shadow-md' : ''}
          `}
        >
          <div className="p-5 flex flex-col gap-2 pointer-events-none">
            <div className="pointer-events-auto">
              <ArticleTitle
                href={fullUrl}
                isRemoved={isRemoved}
                isRead={isRead}
                title={article.title}
                onLinkClick={(e) => {
                  if (isRemoved) {
                    e.preventDefault()
                    return
                  }
                  e.stopPropagation()
                  if (!isRead) toggleRead()
                }}
              />
            </div>

            {!isRemoved && (
              <div className="pointer-events-auto">
                <ArticleMeta
                  domain={domain}
                  articleMeta={article.articleMeta}
                  isRead={isRead}
                  tldrLoading={tldr.loading}
                  onRemove={(e) => {
                    e.stopPropagation()
                    handleSwipeComplete()
                  }}
                  removeDisabled={stateLoading}
                />
              </div>
            )}

            {!isRemoved && tldr.status === 'error' && (
              <TldrError message={tldr.errorMessage} />
            )}

            {!isRemoved && tldr.expanded && tldr.html && (
              <div className="pointer-events-auto">
                <ZenModeOverlay
                  title={article.title}
                  html={tldr.html}
                  onClose={() => toggleTldrWithTracking(() => tldr.collapse())}
                />
              </div>
            )}
          </div>
        </m.div>
      </m.div>
    </LazyMotion>
  )
}

export default ArticleCard
