import { useMemo } from 'react'
import { toYaml } from '../lib/yamlLog'
import { tokenizeYamlLine } from '../lib/yamlTokens'

const TOKEN_CLASS = {
  listMarker: 'text-emerald-400/70',
  key: 'text-emerald-300',
  colon: 'text-emerald-200/60',
  space: '',
  string: 'text-amber-200',
  number: 'text-cyan-300',
  bool: 'text-purple-300',
  null: 'text-slate-500 italic',
  plain: 'text-emerald-200',
}

const INDENT_CHAR = '·'

function IndentSpan() {
  return <span className="text-emerald-200/20" aria-hidden>{`${INDENT_CHAR} `}</span>
}

function ToggleMarker() {
  return (
    <>
      <span className="text-emerald-400/60 group-open:hidden">▶ </span>
      <span className="text-emerald-400/60 hidden group-open:inline">▼ </span>
    </>
  )
}

function renderTokens(tokens, foldMarker = null) {
  return tokens.map((token) => {
    if (token.type === 'indent') return <IndentSpan key={token.id} />
    if (token.type === 'listMarker' && foldMarker) return <span key={token.id}>{foldMarker}</span>
    return (
      <span key={token.id} className={TOKEN_CLASS[token.type] || ''}>{token.text}</span>
    )
  })
}

function YamlLine({ line }) {
  const { tokens } = tokenizeYamlLine(line)
  return <div className="whitespace-pre">{renderTokens(tokens)}</div>
}

function FoldGroup({ headLine, body }) {
  const { tokens } = tokenizeYamlLine(headLine)
  return (
    <details className="group">
      <summary className="block whitespace-pre cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        {renderTokens(tokens, <ToggleMarker />)}
      </summary>
      {body.map((bodyLine) => (
        <YamlLine key={bodyLine.id} line={bodyLine.text} />
      ))}
    </details>
  )
}

function groupYamlLines(lines) {
  const items = []
  let cursor = 0
  let bodyId = 0
  while (cursor < lines.length) {
    const line = lines[cursor]
    const foldMatch = line.match(/^(\s*)- url: \S/)
    if (!foldMatch) {
      items.push({ id: items.length, kind: 'line', line })
      cursor += 1
      continue
    }
    const baseIndent = foldMatch[1].length
    const body = []
    let scan = cursor + 1
    while (scan < lines.length) {
      const next = lines[scan]
      if (next.trim() === '') {
        scan += 1
        continue
      }
      const nextIndent = next.length - next.trimStart().length
      if (nextIndent <= baseIndent) break
      bodyId += 1
      body.push({ id: `body-${bodyId}`, text: next })
      scan += 1
    }
    if (body.length === 0) {
      items.push({ id: items.length, kind: 'line', line })
    } else {
      items.push({ id: items.length, kind: 'fold', headLine: line, body })
    }
    cursor = scan
  }
  return items
}

function YamlView({ value }) {
  const text = useMemo(() => toYaml(value), [value])
  const items = useMemo(() => groupYamlLines(text.split('\n')), [text])

  return (
    <div className="font-mono text-[11px] leading-snug text-emerald-200">
      {items.map((item) => (
        item.kind === 'fold'
          ? <FoldGroup key={item.id} headLine={item.headLine} body={item.body} />
          : <YamlLine key={item.id} line={item.line} />
      ))}
    </div>
  )
}

export default YamlView

