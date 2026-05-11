import { createElement, useMemo } from 'react'
import { markdownToHtml } from '../lib/markdownUtils'
import { overlayProseClassName } from './BaseOverlay'
import OverlayLink from './OverlayLink'

const TEXT_NODE = 3
const ELEMENT_NODE = 1

const VOID_ELEMENT_NAMES = new Set([
  'area',
  'base',
  'br',
  'col',
  'embed',
  'hr',
  'img',
  'input',
  'link',
  'meta',
  'param',
  'source',
  'track',
  'wbr',
])

const ATTRIBUTE_NAME_BY_HTML_NAME = Object.freeze({
  class: 'className',
  for: 'htmlFor',
  tabindex: 'tabIndex',
  colspan: 'colSpan',
  rowspan: 'rowSpan',
  readonly: 'readOnly',
  maxlength: 'maxLength',
  minlength: 'minLength',
  autocomplete: 'autoComplete',
  autofocus: 'autoFocus',
  contenteditable: 'contentEditable',
})

function toReactAttributeName(attributeName) {
  return ATTRIBUTE_NAME_BY_HTML_NAME[attributeName] ?? attributeName
}

function toReactStyleName(styleName) {
  if (styleName.startsWith('--')) return styleName
  return styleName.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())
}

function parseStyleAttribute(styleAttribute) {
  return styleAttribute
    .split(';')
    .map(declaration => declaration.trim())
    .filter(Boolean)
    .reduce((style, declaration) => {
      const [rawName, ...rawValueParts] = declaration.split(':')
      const name = rawName.trim()
      const value = rawValueParts.join(':').trim()
      if (!name || !value) return style
      style[toReactStyleName(name)] = value
      return style
    }, {})
}

function attributesToProps(element, key) {
  const props = { key }

  for (const attribute of element.attributes) {
    const attributeName = attribute.name.toLowerCase()
    if (attributeName === 'style') {
      const style = parseStyleAttribute(attribute.value)
      if (Object.keys(style).length > 0) props.style = style
      continue
    }
    props[toReactAttributeName(attributeName)] = attribute.value
  }

  return props
}

function nodeToReact(node, key) {
  if (node.nodeType === TEXT_NODE) return node.textContent
  if (node.nodeType !== ELEMENT_NODE) return null

  const element = node
  const tagName = element.tagName.toLowerCase()
  const children = Array.from(element.childNodes)
    .map((child, index) => nodeToReact(child, `${key}-${index}`))
    .filter(child => child !== null)

  if (tagName === 'a') {
    return createElement(
      OverlayLink,
      {
        key,
        href: element.getAttribute('href') ?? '',
        title: element.getAttribute('title') ?? undefined,
      },
      children
    )
  }

  const props = attributesToProps(element, key)
  if (VOID_ELEMENT_NAMES.has(tagName)) return createElement(tagName, props)
  return createElement(tagName, props, children)
}

function htmlToReact(html) {
  const parsedDocument = new DOMParser().parseFromString(html, 'text/html')
  return Array.from(parsedDocument.body.childNodes)
    .map((node, index) => nodeToReact(node, `root-${index}`))
    .filter(node => node !== null)
}

function OverlayMarkdown({ markdown }) {
  // If need to improve design: render markdown from an AST, not sanitized HTML → DOMParser → React. Current design is because current pipeline is marked + KaTeX + DOMPurify. Cleaner: use a React markdown/rehype pipeline and override link nodes directly.
  const html = useMemo(() => markdownToHtml(markdown), [markdown])
  const content = useMemo(() => htmlToReact(html), [html])
  return <div className={overlayProseClassName}>{content}</div>
}

export default OverlayMarkdown
