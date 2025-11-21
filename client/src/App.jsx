import { useState, useEffect } from 'react'
import CacheToggle from './components/CacheToggle'
import ScrapeForm from './components/ScrapeForm'
import ResultsDisplay from './components/ResultsDisplay'
import { loadFromCache } from './lib/scraper'
import './App.css'

function App() {
  const [results, setResults] = useState(null)
  const [copying, setCopying] = useState(null)

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

  const handleContextCopy = async (contextType) => {
    setCopying(contextType)
    try {
      const response = await fetch('/api/generate-context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_type: contextType })
      })

      const result = await response.json()

      if (result.success) {
        await navigator.clipboard.writeText(result.content)
        setTimeout(() => setCopying(null), 1000)
      } else {
        console.error('Failed to generate context:', result.error)
        setCopying(null)
      }
    } catch (err) {
      console.error('Failed to copy context:', err)
      setCopying(null)
    }
  }

  return (
    <div className="container">
      <h1>Newsletter Aggregator</h1>

      <div className="context-buttons">
        <button
          onClick={() => handleContextCopy('server')}
          disabled={copying === 'server'}
          className="context-btn"
        >
          📋 {copying === 'server' ? 'Copied!' : 'server'}
        </button>
        <button
          onClick={() => handleContextCopy('client')}
          disabled={copying === 'client'}
          className="context-btn"
        >
          📋 {copying === 'client' ? 'Copied!' : 'client'}
        </button>
        <button
          onClick={() => handleContextCopy('docs')}
          disabled={copying === 'docs'}
          className="context-btn"
        >
          📋 {copying === 'docs' ? 'Copied!' : 'docs'}
        </button>
        <button
          onClick={() => handleContextCopy('all')}
          disabled={copying === 'all'}
          className="context-btn"
        >
          📋 {copying === 'all' ? 'Copied!' : 'all'}
        </button>
      </div>

      <CacheToggle />

      <ScrapeForm onResults={setResults} />

      {results && <ResultsDisplay results={results} />}
    </div>
  )
}

export default App
