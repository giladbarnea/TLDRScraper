export function getFaviconUrl(hostname) {
  if (!hostname) return null

  const params = new URLSearchParams({
    domain_url: `https://${hostname}`,
    sz: '64',
  })

  return `https://www.google.com/s2/favicons?${params.toString()}`
}
