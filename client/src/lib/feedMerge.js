const SERVER_ORIGIN_FIELDS = ['url', 'title', 'articleMeta', 'issueDate', 'category', 'sourceId', 'section', 'sectionEmoji', 'sectionOrder', 'newsletterType']

export function mergePreservingLocalState(freshPayload, localPayload) {
  if (!localPayload) return freshPayload

  const localArticlesByUrl = new Map(localPayload.articles.map((article) => [article.url, article]))

  return {
    ...freshPayload,
    articles: freshPayload.articles.map((article) => {
      const localArticle = localArticlesByUrl.get(article.url)
      if (!localArticle) {
        return { ...article, issueDate: freshPayload.date }
      }

      const freshFields = {}
      for (const field of SERVER_ORIGIN_FIELDS) {
        freshFields[field] = article[field]
      }
      freshFields.issueDate = freshPayload.date

      return { ...localArticle, ...freshFields }
    }),
    digest: localPayload.digest
  }
}
