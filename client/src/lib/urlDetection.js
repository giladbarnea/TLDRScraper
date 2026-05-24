import { isTopLevelDomain } from './topLevelDomains'

export function isLikelyUrl(input) {
  if (typeof input !== 'string') return false
  let stripped = input.trim()
  stripped = stripped.replace(/^https?:\/\//i, '')
  stripped = stripped.replace(/^www\./i, '')
  const hostname = stripped.split(/[/?#]/)[0]
  const parts = hostname.split('.')
  if (!parts[0] || !parts[1]) return false
  return isTopLevelDomain(parts[parts.length - 1])
}
