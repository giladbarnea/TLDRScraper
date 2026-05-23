import { Link2, Loader2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { readApiResponse } from '../lib/apiError'
import { emitToast } from '../lib/toastBus'
import { isLikelyUrl } from '../lib/urlDetection'
import { ingestDayPayload } from '../store/articleStore'

const IDLE = 'idle'
const SUBMITTING = 'submitting'
const ERROR = 'error'

async function postUrlToArticle(url) {
  const response = await window.fetch('/api/url-to-article', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  return readApiResponse(response, 'POST /api/url-to-article')
}

function humanizeError(message) {
  if (!message) return 'Something went wrong.'
  if (/firecrawl|jina|curl|timed out|timeout|network/i.test(message)) return "Couldn't reach that URL."
  if (/missing field|missing url/i.test(message)) return 'No URL provided.'
  if (message.length > 80) return `${message.slice(0, 80)}…`
  return message
}

function deriveDataState({ status, hasInput, isValid }) {
  if (status === SUBMITTING) return 'submitting'
  if (status === ERROR) return 'error'
  if (!hasInput) return 'empty'
  return isValid ? 'valid' : 'pending'
}

// iOS Safari's fixed-position ignores the keyboard; visualViewport tracks what's visible.
function useVisualViewportInsets() {
  const [insets, setInsets] = useState({ top: 0, height: null })
  useEffect(() => {
    const vv = window.visualViewport
    if (!vv) return
    function update() {
      setInsets({ top: vv.offsetTop, height: vv.height })
    }
    update()
    vv.addEventListener('resize', update)
    vv.addEventListener('scroll', update)
    return () => {
      vv.removeEventListener('resize', update)
      vv.removeEventListener('scroll', update)
    }
  }, [])
  return insets
}

function AddUrlOverlay({ onClose }) {
  const [value, setValue] = useState('')
  const [status, setStatus] = useState(IDLE)
  const [errorMessage, setErrorMessage] = useState(null)
  const inputRef = useRef(null)
  const insets = useVisualViewportInsets()

  const trimmed = value.trim()
  const hasInput = trimmed.length > 0
  const isValid = hasInput && isLikelyUrl(trimmed)
  const dataState = deriveDataState({ status, hasInput, isValid })

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    function handleKey(event) {
      if (event.key !== 'Escape') return
      event.preventDefault()
      if (status !== SUBMITTING) onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [status, onClose])

  async function submitUrl(url) {
    setStatus(SUBMITTING)
    setErrorMessage(null)
    try {
      const result = await postUrlToArticle(url)
      if (!result.payload) throw new Error('Response missing payload')
      ingestDayPayload(result.payload)
      emitToast({ title: `Added: ${url}`, url })
      onClose()
    } catch (error) {
      console.error('add-url failed:', error)
      setStatus(ERROR)
      setErrorMessage(humanizeError(error.message))
    }
  }

  function handleInputChange(event) {
    const next = event.target.value
    setValue(next)
    if (status === ERROR) {
      setStatus(IDLE)
      setErrorMessage(null)
    }
    if (status !== SUBMITTING && isLikelyUrl(next.trim())) {
      submitUrl(next.trim())
    }
  }

  function handleBackdropClick() {
    if (status !== SUBMITTING) onClose()
  }

  const showError = status === ERROR
  const inputBorderClass = showError
    ? 'border-red-300 focus:border-red-400'
    : 'border-slate-200 focus:border-slate-300'

  const overlayStyle = insets.height
    ? { top: insets.top, height: insets.height }
    : undefined

  return createPortal(
    <div
      data-testid="add-url-overlay"
      data-state={dataState}
      onMouseDown={handleBackdropClick}
      style={overlayStyle}
      className="fixed inset-x-0 top-0 h-[100dvh] z-[140] flex items-center justify-center bg-slate-900/30 backdrop-blur-sm animate-overlay-menu-enter"
    >
      <div
        onMouseDown={(event) => event.stopPropagation()}
        className="w-full max-w-3xl mx-6 min-h-[33dvh] flex items-center justify-center bg-white rounded-3xl shadow-elevated border border-slate-200/60 p-6 sm:p-10"
      >
        <div className="w-full">
          <div className="relative">
            <input
              ref={inputRef}
              type="url"
              inputMode="url"
              value={value}
              onChange={handleInputChange}
              disabled={status === SUBMITTING}
              data-testid="add-url-input"
              data-valid={isValid}
              placeholder="Paste a URL"
              className={`w-full bg-slate-50 text-xl sm:text-2xl text-slate-900 placeholder:text-slate-300 rounded-2xl border ${inputBorderClass} focus:outline-none px-6 py-4 pr-14 transition-colors disabled:opacity-60`}
              spellCheck={false}
              autoCapitalize="off"
              autoCorrect="off"
              autoComplete="off"
            />
            {status === SUBMITTING && (
              <span
                data-testid="add-url-spinner"
                role="status"
                aria-label="Submitting"
                className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
              >
                <Loader2 size={22} className="animate-spin" />
              </span>
            )}
            <span
              data-testid="add-url-status"
              data-status={status}
              data-valid={isValid}
              className="sr-only"
            >
              {dataState}{errorMessage ? `: ${errorMessage}` : ''}
            </span>
          </div>
          {showError && (
            <p
              data-testid="add-url-error"
              role="alert"
              className="mt-3 px-2 text-sm text-red-600"
            >
              {errorMessage}
            </p>
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}

function AddUrlButton({ open, onOpenChange }) {
  return (
    <>
      <button
        type="button"
        data-testid="add-url-button"
        data-state={open ? 'open' : 'closed'}
        onClick={() => onOpenChange(true)}
        className={`group flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${open ? 'bg-brand-50 text-brand-600' : 'hover:bg-white hover:shadow-md text-slate-400'}`}
        title="Add URL"
        aria-label="Add URL"
      >
        <Link2 size={18} className="transition-colors" />
      </button>
      {open && <AddUrlOverlay onClose={() => onOpenChange(false)} />}
    </>
  )
}

export default AddUrlButton
