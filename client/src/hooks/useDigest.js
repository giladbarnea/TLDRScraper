import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { useMemo, useState } from 'react'
import { fetchDigest } from '../lib/digest'
import { acquireZenOverlayLock, releaseZenOverlayLock } from './useZenOverlayLock'

export function useDigest() {
  const [status, setStatus] = useState('idle')
  const [errorMessage, setErrorMessage] = useState(null)
  const [digestData, setDigestData] = useState(null)
  const [expanded, setExpanded] = useState(false)

  const html = useMemo(() => {
    const markdown = digestData?.digest_markdown || ''
    if (!markdown) return ''
    try {
      return DOMPurify.sanitize(marked.parse(markdown), {
        ADD_TAGS: ['annotation', 'semantics']
      })
    } catch {
      return ''
    }
  }, [digestData?.digest_markdown])

  const generate = async (articles) => {
    if (!articles.length) {
      throw new Error('Select at least one article')
    }
    setStatus('loading')
    setErrorMessage(null)
    const result = await fetchDigest(articles)
    setDigestData(result)
    setStatus('available')
    if (acquireZenOverlayLock(result.digest_id)) {
      setExpanded(true)
    }
    return result
  }

  const collapse = () => {
    if (!digestData?.digest_id) return
    releaseZenOverlayLock(digestData.digest_id)
    setExpanded(false)
  }

  return {
    status,
    errorMessage,
    digestData,
    html,
    expanded,
    loading: status === 'loading',
    isAvailable: status === 'available',
    isError: status === 'error',
    generate: async (articles) => {
      try {
        return await generate(articles)
      } catch (error) {
        setStatus('error')
        setErrorMessage(error.message)
        throw error
      }
    },
    collapse,
  }
}
