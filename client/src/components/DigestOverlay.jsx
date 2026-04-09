import { BookOpen } from 'lucide-react'
import BaseOverlay, { overlayProseClassName } from './BaseOverlay'

function DigestOverlay({ html, expanded, articleCount, errorMessage, onClose, onMarkRemoved }) {
  return (
    <BaseOverlay
      expanded={expanded}
      headerContent={(
        <div className="flex items-center gap-2">
          <BookOpen size={16} className="text-slate-500" />
          <span className="text-sm text-slate-500 font-medium">
            {articleCount} {articleCount === 1 ? 'article' : 'articles'}
          </span>
        </div>
      )}
      onClose={onClose}
      onMarkRemoved={onMarkRemoved}
    >
      {errorMessage && !html ? (
        <div className="text-sm text-red-500 bg-red-50 p-4 rounded-lg">{errorMessage}</div>
      ) : (
        <div className={overlayProseClassName} dangerouslySetInnerHTML={{ __html: html }} />
      )}
    </BaseOverlay>
  )
}

export default DigestOverlay
