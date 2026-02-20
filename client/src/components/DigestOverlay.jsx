import { Sparkles } from 'lucide-react'
import ZenOverlayShell from './ZenOverlayShell'

function DigestOverlay({ digestHtml, articleCount, onClose }) {
  return (
    <ZenOverlayShell
      onClose={onClose}
      headerCenter={(
        <div className="text-sm text-slate-500 font-medium truncate">
          <Sparkles size={14} className="inline mr-1" />
          {articleCount} selected articles
        </div>
      )}
      headerRight={<span className="w-9" />}
    >
      {() => (
        <div className="px-6 pt-2 pb-5 md:px-8 md:pt-3 md:pb-6">
          <div className="max-w-3xl mx-auto">
            <div
              className="prose prose-slate max-w-none font-serif text-slate-700 leading-relaxed text-lg prose-p:my-3 prose-headings:text-slate-900 prose-headings:tracking-tight prose-h1:text-2xl prose-h1:font-bold prose-h2:text-xl prose-h2:font-semibold prose-h3:text-lg prose-h3:font-semibold prose-blockquote:border-slate-200 prose-strong:text-slate-900"
              dangerouslySetInnerHTML={{ __html: digestHtml }}
            />
          </div>
        </div>
      )}
    </ZenOverlayShell>
  )
}

export default DigestOverlay
