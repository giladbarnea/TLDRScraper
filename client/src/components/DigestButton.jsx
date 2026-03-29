function extractArticleDescriptors(selectedIds, payloads) {
  const allArticles = payloads.flatMap((payload) => payload.articles)
  return allArticles
    .filter((article) => selectedIds.has(`article-${article.url}`))
    .map(({ url, title, category, sourceId }) => ({ url, title, category, sourceId }))
}

function DigestButton({ selectedIds, payloads, onTrigger, isLoading, isSelectMode }) {
  if (!isSelectMode) return null

  const isDisabled = selectedIds.size < 2 || isLoading

  function handleClick() {
    const descriptors = extractArticleDescriptors(selectedIds, payloads)
    onTrigger(descriptors)
  }

  return (
    <button
      onClick={handleClick}
      disabled={isDisabled}
      className="flex items-center gap-1.5 bg-slate-900 text-white px-3 py-1.5 rounded-full text-sm font-medium disabled:opacity-40 transition-opacity"
    >
      {isLoading ? 'Generating...' : 'Digest'}
    </button>
  )
}

export default DigestButton
