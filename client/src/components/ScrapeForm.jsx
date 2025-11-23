import { useActionState, useEffect, useState } from 'react'
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { scrapeNewsletters } from '../lib/scraper'
import './ScrapeForm.css'

function ScrapeForm({ onResults }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [cacheEnabled] = useSupabaseStorage('cache:enabled', true)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const today = new Date()
    const threeDaysAgo = new Date(today)
    threeDaysAgo.setDate(today.getDate() - 3)
    setEndDate(today.toISOString().split('T')[0])
    setStartDate(threeDaysAgo.toISOString().split('T')[0])
  }, [])

  const [state, formAction, isPending] = useActionState(
    async (previousState, formData) => {
      const start = formData.get('start_date')
      const end = formData.get('end_date')

      const startDateObj = new Date(start)
      const endDateObj = new Date(end)
      const daysDiff = Math.ceil((endDateObj - startDateObj) / (1000 * 60 * 60 * 24))

      if (startDateObj > endDateObj) {
        return { error: 'Start date must be before or equal to end date.' }
      }
      if (daysDiff >= 31) {
        return { error: 'Date range cannot exceed 31 days. Please select a smaller range.' }
      }

      setProgress(50)

      try {
        const results = await scrapeNewsletters(start, end, cacheEnabled)
        setProgress(100)
        onResults(results)
        return { success: true }
      } catch (err) {
        setProgress(0)
        return { error: err.message || 'Network error' }
      }
    },
    { success: false }
  )

  const validationError = (() => {
    if (!startDate || !endDate) return null

    const start = new Date(startDate)
    const end = new Date(endDate)
    const daysDiff = Math.ceil((end - start) / (1000 * 60 * 60 * 24))

    if (start > end) {
      return 'Start date must be before or equal to end date.'
    }
    if (daysDiff >= 31) {
      return 'Date range cannot exceed 31 days. Please select a smaller range.'
    }
    return null
  })()

  return (
    <div>
      <form id="scrapeForm" action={formAction}>
        <div className="form-group">
          <label htmlFor="start_date">Start Date:</label>
          <input
            id="start_date"
            name="start_date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="end_date">End Date:</label>
          <input
            id="end_date"
            name="end_date"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            required
          />
        </div>

        <button
          id="scrapeBtn"
          type="submit"
          disabled={isPending || !!validationError}
          data-testid="scrape-btn"
        >
          {isPending ? 'Scraping...' : 'Scrape Newsletters'}
        </button>
      </form>

      {isPending && (
        <div className="progress">
          <div id="progress-text">
            Scraping newsletters... This may take several minutes.
          </div>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {validationError && (
        <div className="error" role="alert">
          {validationError}
        </div>
      )}

      {state.error && (
        <div className="error" role="alert">
          Error: {state.error}
        </div>
      )}
    </div>
  )
}

export default ScrapeForm
