export function getSelectedArticles(selectedIds, payloads) {
  if (!payloads) return []

  const selectedArticles = []

  for (const payload of payloads) {
    for (const article of payload.articles) {
      if (selectedIds.has(`article-${article.url}`)) {
        selectedArticles.push(article)
      }
    }
  }

  return selectedArticles
}

export function extractSelectedArticleDescriptors(selectedArticles) {
  return selectedArticles.map(({ url, title, category, sourceId }) => ({
    url,
    title,
    category,
    sourceId
  }))
}

export function groupSelectedByDate(selectedArticles) {
  const groupedArticlesByDate = new Map()

  for (const article of selectedArticles) {
    if (!groupedArticlesByDate.has(article.issueDate)) {
      groupedArticlesByDate.set(article.issueDate, [])
    }

    groupedArticlesByDate.get(article.issueDate).push(article)
  }

  return groupedArticlesByDate
}
