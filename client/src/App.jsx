import { useState, useEffect } from 'react'
import CacheToggle from './components/CacheToggle'
import ScrapeForm from './components/ScrapeForm'
import ResultsDisplay from './components/ResultsDisplay'
import { loadFromCache } from './lib/scraper'
import './App.css'

function App() {
  const [results, setResults] = useState(null)
  const [copying, setCopying] = useState(null)
  const [copyError, setCopyError] = useState(null)

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

  const fallbackCopy = (text) => {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    try {
      document.execCommand('copy')
      console.log('Fallback copy succeeded')
      return true
    } catch (err) {
      console.error('Fallback copy failed:', err)
      return false
    } finally {
      document.body.removeChild(textarea)
    }
  }

  const handleContextCopy = async (contextType) => {
    console.log(`[handleContextCopy] Starting copy for: ${contextType}`)
    setCopying(contextType)
    setCopyError(null)

    try {
      console.log(`[handleContextCopy] Fetching context...`)
      const response = await fetch('/api/generate-context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_type: contextType })
      })

      console.log(`[handleContextCopy] Response status: ${response.status}`)
      const result = await response.json()
      console.log(`[handleContextCopy] Result success: ${result.success}, content length: ${result.content?.length || 0}`)

      if (result.success) {
        try {
          await navigator.clipboard.writeText(result.content)
          console.log(`[handleContextCopy] Clipboard write succeeded`)
          setTimeout(() => setCopying(null), 1000)
        } catch (clipErr) {
          console.error(`[handleContextCopy] Clipboard API failed:`, clipErr)
          console.log(`[handleContextCopy] Trying fallback method...`)

          if (fallbackCopy(result.content)) {
            setTimeout(() => setCopying(null), 1000)
          } else {
            setCopyError(`Clipboard access denied. Content length: ${result.content.length}`)
            setCopying(null)
          }
        }
      } else {
        console.error('Failed to generate context:', result.error)
        setCopyError(`Server error: ${result.error}`)
        setCopying(null)
      }
    } catch (err) {
      console.error('Failed to copy context:', err)
      setCopyError(`Network error: ${err.message}`)
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

      {copyError && (
        <div className="copy-error">
          {copyError}
        </div>
      )}

      <CacheToggle />

      <ScrapeForm onResults={setResults} />

      {results && <ResultsDisplay results={results} />}
    </div>
  )
}

export default App
