import { useState, useEffect } from 'react'
import CacheToggle from './components/CacheToggle'
import ScrapeForm from './components/ScrapeForm'
import ResultsDisplay from './components/ResultsDisplay'
import { loadFromCache } from './lib/scraper'
import './App.css'

function App() {
  const [results, setResults] = useState(null)

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
    <div className="container">
      <h1>Newsletter Aggregator</h1>

      <CacheToggle />

      <ScrapeForm onResults={setResults} />

      {results && <ResultsDisplay results={results} />}
    </div>
  )
}

export default App
