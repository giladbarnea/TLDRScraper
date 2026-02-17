import ArticleCard from './ArticleCard'

function ArticleList({ articles }) {
  const sortedArticles = [...articles].sort((a, b) => {
    const stateA = a.removed ? 1 : 0
    const stateB = b.removed ? 1 : 0

    if (stateA !== stateB) return stateA - stateB

    return (a.originalOrder ?? 0) - (b.originalOrder ?? 0)
  })

  return (
    <div>
      {sortedArticles.map((article) => (
        <ArticleCard key={article.url} article={article} />
      ))}
    </div>
  )
}

export default ArticleList
