import DOMPurify from 'dompurify'
import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'

marked.use(markedKatex({ throwOnError: false }))

export function markdownToHtml(markdown) {
  if (!markdown) return ''

  try {
    const rawHtml = marked.parse(markdown)
    return DOMPurify.sanitize(rawHtml, {
      ADD_TAGS: ['annotation', 'semantics']
    })
  } catch (error) {
    console.error('Failed to parse markdown:', error)
    return ''
  }
}
