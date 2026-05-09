/**
 * Pure tokenizer for a single line of YAML output produced by `yaml.stringify`
 * with `indent: 2, indentSeq: true`. The output drives both the indent-guide
 * rendering and basic syntax highlighting in `YamlView`.
 *
 * Token shape (returned as `tokens` array):
 *   { type: 'indent',      text: '  ' }      (one per indent level, always 2 spaces of source)
 *   { type: 'listMarker',  text: '- ' }      (only for array entries)
 *   { type: 'key',         text: 'foo' }     (object key, may be quoted)
 *   { type: 'colon',       text: ':' }
 *   { type: 'space',       text: ' ' }       (between colon and value)
 *   { type: 'string'|'number'|'bool'|'null'|'plain', text: '...' }
 *
 * Empty lines yield `{ tokens: [], indent: 0, isListItem: false }`.
 */

const INDENT_SIZE = 2

function classifyValue(text) {
  const trimmed = text.trim()
  if (trimmed === '' || trimmed === '~' || trimmed === 'null') return 'null'
  if (trimmed === 'true' || trimmed === 'false') return 'bool'
  if (/^-?\d+(\.\d+)?$/.test(trimmed)) return 'number'
  if (trimmed === '[]' || trimmed === '{}') return 'plain'
  return 'string'
}

function findUnquotedKeyColon(rest) {
  let inQuote = false
  let quoteChar = null
  for (let charIndex = 0; charIndex < rest.length; charIndex += 1) {
    const character = rest[charIndex]
    if (inQuote) {
      if (character === '\\' && charIndex + 1 < rest.length) {
        charIndex += 1
        continue
      }
      if (character === quoteChar) inQuote = false
      continue
    }
    if (character === '"' || character === "'") {
      inQuote = true
      quoteChar = character
      continue
    }
    if (character === ':' && (charIndex === rest.length - 1 || rest[charIndex + 1] === ' ')) {
      return charIndex
    }
  }
  return -1
}

function pushToken(tokens, type, text) {
  tokens.push({ id: tokens.length, type, text })
}

export function tokenizeYamlLine(line) {
  const tokens = []
  const trimmed = line.replace(/\s+$/, '')
  if (trimmed === '') {
    return { tokens: [], indent: 0, indentLevels: 0, isListItem: false }
  }

  let cursor = 0
  while (cursor < trimmed.length && trimmed[cursor] === ' ') cursor += 1
  const indent = cursor
  const indentLevels = Math.floor(indent / INDENT_SIZE)
  for (let level = 0; level < indentLevels; level += 1) {
    pushToken(tokens, 'indent', ' '.repeat(INDENT_SIZE))
  }

  let isListItem = false
  if (trimmed[cursor] === '-' && (cursor + 1 === trimmed.length || trimmed[cursor + 1] === ' ')) {
    pushToken(tokens, 'listMarker', '- ')
    cursor += 2
    isListItem = true
  }

  const rest = trimmed.slice(cursor)
  if (rest === '') {
    return { tokens, indent, indentLevels, isListItem }
  }

  const colonIndex = findUnquotedKeyColon(rest)
  if (colonIndex === -1) {
    pushToken(tokens, classifyValue(rest), rest)
    return { tokens, indent, indentLevels, isListItem }
  }

  const keyText = rest.slice(0, colonIndex)
  const afterColon = rest.slice(colonIndex + 1)
  pushToken(tokens, 'key', keyText)
  pushToken(tokens, 'colon', ':')

  const valueStart = afterColon.length - afterColon.trimStart().length
  if (valueStart > 0) {
    pushToken(tokens, 'space', afterColon.slice(0, valueStart))
  }
  const valueText = afterColon.slice(valueStart)
  if (valueText !== '') {
    pushToken(tokens, classifyValue(valueText), valueText)
  }

  return { tokens, indent, indentLevels, isListItem }
}
