const SUMMARY_STYLE_FIELDS = Object.freeze([
  'overlay_panel',
  'overlay_content_wrapper',
  'overlay_content_max_width',
  'prose_root',
  'paragraph',
  'heading_1',
  'heading_2',
  'heading_3',
  'blockquote',
  'strong',
])

const ALLOWED_STYLE_PROPERTIES = new Set([
  'font-family',
  'font-size',
  'font-weight',
  'font-style',
  'line-height',
  'letter-spacing',
  'word-spacing',
  'text-transform',
  'margin',
  'margin-top',
  'margin-bottom',
  'margin-left',
  'margin-right',
  'padding',
  'padding-top',
  'padding-bottom',
  'padding-left',
  'padding-right',
  'max-width',
  'width',
])

const BLOCKED_VALUE_TOKENS = ['calc(', 'var(', 'url(', 'clamp(', 'min(', 'max(', 'attr(', '!important']

function isSimpleCssValue(propertyValue) {
  if (!propertyValue) return false
  const normalizedValue = propertyValue.toLowerCase()
  if (BLOCKED_VALUE_TOKENS.some(token => normalizedValue.includes(token))) return false
  return /^[^{};]+$/.test(propertyValue)
}

function parseCssDeclarationString(styleString) {
  const declarations = {}
  for (const declaration of styleString.split(';')) {
    if (!declaration.includes(':')) continue
    const [propertyName, ...valueParts] = declaration.split(':')
    const normalizedPropertyName = propertyName.trim().toLowerCase()
    if (!ALLOWED_STYLE_PROPERTIES.has(normalizedPropertyName)) continue

    const propertyValue = valueParts.join(':').trim()
    if (!isSimpleCssValue(propertyValue)) continue
    declarations[normalizedPropertyName] = propertyValue
  }
  return declarations
}

function convertDeclarationMapToReactStyle(declarationMap) {
  const reactStyle = {}
  for (const [propertyName, propertyValue] of Object.entries(declarationMap)) {
    const camelCaseName = propertyName.replace(/-([a-z])/g, (_, character) => character.toUpperCase())
    reactStyle[camelCaseName] = propertyValue
  }
  return reactStyle
}

export function parseSummaryStylePayload(payloadText) {
  const parsedPayload = JSON.parse(payloadText)

  const parsedStyle = {}
  for (const fieldName of SUMMARY_STYLE_FIELDS) {
    const styleString = String(parsedPayload[fieldName] || '')
    const declarationMap = parseCssDeclarationString(styleString)
    parsedStyle[fieldName] = convertDeclarationMapToReactStyle(declarationMap)
  }

  return parsedStyle
}

export function createEmptySummaryStyle() {
  return SUMMARY_STYLE_FIELDS.reduce((accumulator, fieldName) => {
    accumulator[fieldName] = {}
    return accumulator
  }, {})
}


function convertReactStyleToCssDeclarationString(reactStyle) {
  return Object.entries(reactStyle)
    .map(([propertyName, propertyValue]) => {
      const cssPropertyName = propertyName.replace(/[A-Z]/g, character => `-${character.toLowerCase()}`)
      return `${cssPropertyName}: ${propertyValue};`
    })
    .join(' ')
}

export function buildSummaryOverlayCssText(parsedStyle, scopeSelector = '.summary-overlay-content') {
  const cssRules = [
    `${scopeSelector} p { ${convertReactStyleToCssDeclarationString(parsedStyle.paragraph)} }`,
    `${scopeSelector} h1 { ${convertReactStyleToCssDeclarationString(parsedStyle.heading_1)} }`,
    `${scopeSelector} h2 { ${convertReactStyleToCssDeclarationString(parsedStyle.heading_2)} }`,
    `${scopeSelector} h3 { ${convertReactStyleToCssDeclarationString(parsedStyle.heading_3)} }`,
    `${scopeSelector} blockquote { ${convertReactStyleToCssDeclarationString(parsedStyle.blockquote)} }`,
    `${scopeSelector} strong { ${convertReactStyleToCssDeclarationString(parsedStyle.strong)} }`,
  ]
  return cssRules.join(' ')
}
