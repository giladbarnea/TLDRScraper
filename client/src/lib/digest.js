export function extractSelectedArticles(selectedIds, payloads) {
  const selectedArticles = []

  for (const payload of payloads || []) {
    for (const article of payload.articles || []) {
      const componentId = `article-${article.url}`
      if (!selectedIds.has(componentId)) continue
      selectedArticles.push({
        url: article.url,
        title: article.title,
        category: article.category,
      })
    }
  }

  return selectedArticles
}

export async function fetchDigest(articles, effort = 'low') {
  const response = await window.fetch('/api/digest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ articles, effort })
  })
  const data = await response.json()
  if (!data.success) {
    throw new Error(data.error || 'Failed to generate digest')
  }
  return data
}
