import { useArticleSlice } from '../store/articleStore'
import ArticleCard from './ArticleCard'

function LiveArticleCard({ articleKey }) {
  const slice = useArticleSlice(articleKey)
  if (!slice) return null
  const isRemoved = Boolean(slice.removed)
  const originalOrder = slice.originalOrder ?? 0

  return (
    <div style={{ order: isRemoved ? 10_000 + originalOrder : originalOrder }}>
      <ArticleCard articleKey={articleKey} />
    </div>
  )
}

function ArticleList({ articleKeys }) {
  return (
    <div className="flex flex-col">
      {articleKeys.map((key) => (
        <LiveArticleCard key={key} articleKey={key} />
      ))}
    </div>
  )
}

export default ArticleList
