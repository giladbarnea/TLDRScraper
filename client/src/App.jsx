import { useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import CacheToggle from './components/CacheToggle'
import ResultsDisplay from './components/ResultsDisplay'
import ScrapeForm from './components/ScrapeForm'
import { loadFromCache } from './lib/scraper'
import './App.css'

function App() {
  const [results, setResults] = useState(null)
  const [copying, setCopying] = useState(null)
  const [downloadError, setDownloadError] = useState(null)

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
    console.log(`[handleContextCopy] Starting download for: ${contextType}`)
    setCopying(contextType)
    setDownloadError(null)

    try {
      const response = await fetch('/api/generate-context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_type: contextType })
      })

      console.log(`[handleContextCopy] Response status: ${response.status}`)
      const result = await response.json()
      console.log(`[handleContextCopy] Result success: ${result.success}, content length: ${result.content?.length || 0}`)

      if (result.success) {
        const blob = new Blob([result.content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `context-${contextType}.txt`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)

        console.log(`[handleContextCopy] Download triggered`)
        setTimeout(() => setCopying(null), 1000)
      } else {
        console.error('Failed to generate context:', result.error)
        setDownloadError(`Server error: ${result.error}`)
        setCopying(null)
      }
    } catch (err) {
      console.error('Failed to download context:', err)
      setDownloadError(`Network error: ${err.message}`)
      setCopying(null)
    }
  }

  return (
    <div className="container">
      <h1>Newsletter Aggregator</h1>

      <div className="flex gap-2 mb-4">
        {['server', 'client', 'docs', 'all'].map(type => (
          <button
            key={type}
            onClick={() => handleContextCopy(type)}
            disabled={copying === type}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold
                       bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Download size={16} />
            {copying === type ? 'Downloaded!' : type}
          </button>
        ))}
      </div>

      {downloadError && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {downloadError}
        </div>
      )}

      <CacheToggle />

      <ScrapeForm onResults={setResults} />

      {results && <ResultsDisplay results={results} />}
    </div>
  )
}

export default App
