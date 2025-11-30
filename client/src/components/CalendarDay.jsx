import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { getNewsletterScrapeKey } from '../lib/storageKeys'
import FoldableContainer from './FoldableContainer'
import NewsletterDay from './NewsletterDay'

function CalendarDay({ payload }) {
  const [livePayload, , , { loading }] = useSupabaseStorage(
    getNewsletterScrapeKey(payload.date),
    payload
  )

  const date = livePayload?.date ?? payload.date
  const articles = (livePayload?.articles ?? payload.articles).map((article, index) => ({
    ...article,
    originalOrder: index
  }))
  const issues = livePayload?.issues ?? payload.issues ?? []

  const dateObj = new Date(date)
  const niceDate = dateObj.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })
  const isToday = new Date().toDateString() === dateObj.toDateString()

  const allArticlesRemoved = articles.length > 0 && articles.every(a => a.removed)

  const Title = (
    <div className="flex items-baseline gap-3 py-4">
      <h2 className="font-display text-2xl font-bold text-slate-900 tracking-tight">
        {isToday ? 'Today' : niceDate}
      </h2>
      {loading && <span className="text-xs font-medium text-brand-500 animate-pulse">Syncing...</span>}
    </div>
  )

  return (
    <section className="animate-slide-up mb-12">
      <FoldableContainer
        id={`calendar-${date}`}
        title={Title}
        defaultFolded={allArticlesRemoved}
        headerClassName="sticky top-0 z-30 bg-slate-50/95 backdrop-blur-sm border-b border-slate-200/60"
        contentClassName="mt-4"
      >
          <div className="space-y-8">
             {/* Iterate over issues (Newsletters) directly */}
             {issues.map(issue => {
               // Filter articles belonging to this newsletter (issue)
               // The user mentioned "newsletter-days contain categories if exist, otherwise newsletter-days contain articles"
               // We need to know which articles belong to this issue.
               // Previously we grouped by `newsletterType`.
               // Now we rely on `issue` metadata.
               // But `article` objects might not have a direct link to `issue` other than `newsletterType` or `category`.
               // Wait, `issue` has `category` property which is the Newsletter Name (e.g. "TLDR AI").
               // Let's check `scraper.js` or `Feed.jsx` original code.
               // In `Feed.jsx` original: `const categoryArticles = articles.filter((article) => article.category === issue.category)`
               // Wait, `issue.category` was used as the Category Name in the original code?
               // Let's look at the user's screenshot. "TLDR AI" is the header.
               // And "Headlines & Launches" is the sub-header.
               // In the original code:
               // `issue.category` was rendered as `h3`.
               // `ArticleList` rendered sections.
               
               // So:
               // `issue.category` = Newsletter Name (e.g. "TLDR AI") ??
               // OR `issue.category` = Section Name?
               
               // Let's re-read `Feed.jsx` original.
               // `issues.map(issue => ...)`
               // `const categoryArticles = articles.filter((article) => article.category === issue.category)`
               // `h3` = `issue.category`.
               
               // If `issue.category` is "TLDR AI", then `articles` must have `category`="TLDR AI".
               // And inside `ArticleList`, it groups by `article.section`.
               
               // So `issue` corresponds to a Newsletter (e.g. TLDR AI).
               // And `article.category` links it to that Newsletter.
               // And `article.section` links it to a Section (e.g. Headlines).
               
               // So my previous assumption that `newsletterType` was the grouping key was probably wrong or redundant?
               // The user said: "categories such as 'ai', 'articles', 'blog' etc popped into existence... they were never part of the app... *real* categories, such as TLDR's 'Headlines & Launches'..."
               
               // In my `CalendarDay.jsx` implementation (the one I wrote in step 46):
               // `const newsletters = articles.reduce((acc, article) => { const type = article.newsletterType || 'Newsletter' ... })`
               // This created the "ai", "articles" folders if `newsletterType` contained those values.
               
               // So I should revert to using `issues` to drive the Newsletter level.
               // And filter articles by `article.category === issue.category`.
               
               const newsletterName = issue.category
               const newsletterArticles = articles.filter(a => a.category === newsletterName)
               
               if (newsletterArticles.length === 0) return null

               return (
                 <NewsletterDay 
                   key={`${date}-${newsletterName}`}
                   date={date}
                   title={newsletterName}
                   issue={issue}
                   articles={newsletterArticles} 
                 />
               )
             })}
          </div>
      </FoldableContainer>
    </section>
  )
}

export default CalendarDay
