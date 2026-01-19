import { Calendar } from 'lucide-react'
import { useEffect, useState } from 'react'
import Feed from './components/Feed'
import ScrapeForm from './components/ScrapeForm'
import { scrapeNewsletters } from './lib/scraper'

function App() {
  const [results, setResults] = useState(null)
  const [showSettings, setShowSettings] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    const today = new Date()
    const twoDaysAgo = new Date(today)
    twoDaysAgo.setDate(today.getDate() - 2)

    const endDate = today.toISOString().split('T')[0]
    const startDate = twoDaysAgo.toISOString().split('T')[0]

    const cacheKey = `scrapeResults:${startDate}:${endDate}`
    const TTL_MS = 10 * 60 * 1000

    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      const { timestamp, data } = JSON.parse(cached)
      if (Date.now() - timestamp < TTL_MS) {
        setResults(data)
        return
      }
    }

    scrapeNewsletters(startDate, endDate, true, controller.signal)
      .then(result => {
        setResults(result)
        try {
          sessionStorage.setItem(cacheKey, JSON.stringify({
            timestamp: Date.now(),
            data: result
          }))
        } catch {}
      })
      .catch(err => {
        if (err.name === 'AbortError') return
        console.error('Failed to load results:', err)
        setResults({ payloads: [], stats: null })
      })

    return () => {
      controller.abort()
    }
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
        <header className="relative z-40 px-6 py-6 bg-transparent">
          <div className="flex justify-between items-center">
            <div>
              <a href="/api/source" className="inline-block">
                <h1 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 hover:text-brand-600 transition-colors cursor-pointer">
                  TLDR<span className="text-brand-500">.</span>
                </h1>
              </a>
              <p className="text-sm font-medium text-slate-500 mt-1">
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

        {/* Main Content */}
        <main className="px-6">
          {!results ? (
             <div className="flex flex-col items-center justify-center py-32 opacity-50 animate-pulse">
                <div className="w-12 h-12 bg-slate-200 rounded-full mb-4"></div>
                <div className="h-4 w-32 bg-slate-200 rounded mb-2"></div>
                <div className="h-3 w-24 bg-slate-100 rounded"></div>
             </div>
          ) : (results.payloads && results.payloads.length > 0) ? (
            <Feed payloads={results.payloads} />
          ) : (
            <div className="flex flex-col items-center justify-center py-32 text-slate-400">
               <p>No newsletters found for this period.</p>
               <button onClick={() => setShowSettings(true)} className="mt-4 text-brand-600 font-medium hover:underline">
                 Open settings to scrape
               </button>
            </div>
          )}
        </main>

      </div>
    </div>
  )
}

export default App
