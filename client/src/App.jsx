import { useState, useEffect } from 'react'
import CacheToggle from './components/CacheToggle'
import ScrapeForm from './components/ScrapeForm'
import ResultsDisplay from './components/ResultsDisplay'
import { loadFromCache } from './lib/scraper'

function App() {
  const [results, setResults] = useState(null)
  const [scrolled, setScrolled] = useState(false)

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

  return (
    <div className="min-h-screen flex justify-center font-sans bg-[#f8fafc] pb-32">
      <div className="w-full max-w-2xl relative">

        {/* Sticky Header */}
        <header
          className={`
            sticky top-0 z-40 px-6 py-5 transition-all duration-300 ease-out mb-6
            ${scrolled ? 'bg-white/90 backdrop-blur-md border-b border-slate-100 shadow-sm' : 'bg-transparent'}
          `}
        >
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <div>
                <h1 className="font-display text-3xl font-extrabold tracking-tight text-slate-900 leading-none">
                  TLDR<span className="text-brand-500">.</span>
                </h1>
              </div>
            </div>
            <div className="flex items-center gap-4">
               <CacheToggle />
            </div>
          </div>
        </header>

        {/* Controls Area */}
        <div className="px-6 mb-10 animate-fade-in">
          <div className="bg-white rounded-2xl p-6 shadow-soft border border-slate-100/80">
             <ScrapeForm onResults={setResults} />
          </div>
        </div>

        {/* Main Content */}
        <main className="px-6">
           {results && <ResultsDisplay results={results} />}
        </main>

      </div>
    </div>
  )
}

export default App
