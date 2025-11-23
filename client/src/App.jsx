import { Calendar, RefreshCw, Settings, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import { loadFromCache } from './lib/scraper'

function App() {
  const [results, setResults] = useState(null)
  const [scrolled, setScrolled] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    const today = new Date()
    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)

    const endDate = today.toISOString().split('T')[0]
    const startDate = threeDaysAgo.toISOString().split('T')[0]

    loadFromCache(startDate, endDate)
      .then(cached => {
        if (cached) {
          setResults(cached)
        }
      })
      .catch(err => {
        console.error('Failed to load cached results:', err)
      })
  }, [])

  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric'
  })

  return (
    <div className="min-h-screen flex justify-center font-sans bg-[#f8fafc] text-slate-900 selection:bg-brand-100 selection:text-brand-900">
      <div className="w-full max-w-3xl relative">

        {/* Header */}
        <header
          className={`
            sticky top-0 z-40 px-6 py-6 transition-all duration-300 ease-out
            ${scrolled ? 'bg-white/90 backdrop-blur-md border-b border-slate-100 shadow-sm' : 'bg-transparent'}
          `}
        >
          <div className="flex justify-between items-center">
            <div>
              <h1 className="font-display text-3xl font-extrabold tracking-tight text-slate-900">
                TLDR<span className="text-brand-500">.</span>
              </h1>
              <p className={`text-sm font-medium text-slate-500 transition-all duration-300 ${scrolled ? 'h-0 opacity-0 overflow-hidden' : 'h-auto opacity-100 mt-1'}`}>
                {currentDate}
              </p>
            </div>

            <div className="flex gap-2">
               <button
                onClick={() => setShowSettings(!showSettings)}
                className={`group flex items-center justify-center w-10 h-10 rounded-full transition-all duration-300 ${showSettings ? 'bg-brand-50 text-brand-600' : 'hover:bg-white hover:shadow-md text-slate-400'}`}
                title="Date Range & Settings"
              >
                <Calendar size={18} className="transition-colors" />
              </button>
            </div>
          </div>

          {/* Settings / Scrape Form Area */}
          <div className={`
              overflow-hidden transition-all duration-500 ease-in-out
              ${showSettings ? 'max-h-[400px] opacity-100 mt-4' : 'max-h-0 opacity-0'}
          `}>
             <div className="bg-white rounded-2xl p-6 shadow-lg border border-slate-100">
                <ScrapeForm onResults={(res) => { setResults(res); setShowSettings(false); }} />
             </div>
          </div>
        </header>

        {/* Minimalist Ticker (Insight) */}
        <div className={`
            px-6 mb-8 transition-all duration-500 ease-in-out
            ${scrolled ? 'opacity-0 h-0 -mt-4 overflow-hidden' : 'opacity-100 h-auto'}
        `}>
          {results?.stats && (
             <div className="bg-white rounded-2xl p-4 shadow-soft border border-slate-50 flex items-start gap-3 animate-fade-in">
               <div className="mt-1 bg-brand-50 p-1.5 rounded-lg">
                 <Zap size={16} className="text-brand-600" />
               </div>
               <p className="text-sm text-slate-600 font-medium leading-relaxed">
                 <span className="font-bold text-slate-900">Daily Update:</span>
                 {' '}Synced <span className="text-brand-600 font-bold">{results.stats.total_articles}</span> articles across {results.stats.dates_processed} days.
                 {results.stats.unique_urls > 0 && <span> ({results.stats.unique_urls} unique).</span>}
               </p>
             </div>
          )}
        </div>

        {/* Main Content */}
        <main className="px-6">
          {!results ? (
             <div className="flex flex-col items-center justify-center py-32 opacity-50 animate-pulse">
                <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
                <div className="h-4 w-32 bg-slate-200 rounded mb-2"></div>
                <div className="h-3 w-24 bg-slate-100 rounded"></div>
             </div>
          ) : (
            <Feed payloads={results.payloads || []} />
          )}
        </main>

      </div>
    </div>
  )
}

export default App
