import { stringify } from 'yaml'

const STRINGIFY_OPTIONS = { indent: 2, indentSeq: true, lineWidth: 0 }

export function toYaml(value) {
  return stringify(value, STRINGIFY_OPTIONS).replace(/\n+$/, '')
}

/**
 * Backwards-compatible helper used by `console.log` callsites.
 * Indents every line of the YAML output by `depth * 2` spaces so the result
 * can be inserted under a parent label like `scrape_request:`.
 */
export function formatYaml(value, depth = 0) {
  const text = toYaml(value)
  if (depth === 0) return text
  const pad = '  '.repeat(depth)
  return text.split('\n').map(line => pad + line).join('\n')
}
