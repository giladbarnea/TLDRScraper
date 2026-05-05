import { useArticleSlice } from '../store/articleStore'
import ArticleCard from './ArticleCard'

function LiveArticleCard({ article }) {
  const liveArticle = useArticleSlice(article.issueDate, article.url)
  const isRemoved = Boolean(liveArticle?.removed)
  const originalOrder = article.originalOrder ?? 0

  return (
    <div style={{ order: isRemoved ? 10_000 + originalOrder : originalOrder }}>
      <ArticleCard article={article} />
    </div>
  )
}

function ArticleList({ articles }) {
  return (
    <div className="flex flex-col">
      {articles.map((article) => (
        <LiveArticleCard key={article.url} article={article} />
      ))}
    </div>
  )
}

export default ArticleList
