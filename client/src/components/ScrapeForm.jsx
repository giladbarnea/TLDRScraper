import { useActionState, useState, useEffect } from 'react'
import { CalendarRange, Loader2, Search, AlertCircle } from 'lucide-react'
import { scrapeNewsletters } from '../lib/scraper'
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'

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

  return (
    <div className="w-full">
      <h2 className="text-lg font-display font-bold text-slate-800 mb-5 flex items-center gap-2">
        <div className="bg-brand-50 p-1.5 rounded-lg">
          <CalendarRange className="w-4 h-4 text-brand-600" />
        </div>
        Select Range
      </h2>

      <form id="scrapeForm" action={formAction} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="start_date" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">From</label>
            <input
              id="start_date"
              name="start_date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className="w-full px-4 py-3 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/10 focus:border-brand-500 transition-all"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="end_date" className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest">To</label>
            <input
              id="end_date"
              name="end_date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className="w-full px-4 py-3 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-700 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-brand-500/10 focus:border-brand-500 transition-all"
            />
          </div>
        </div>

        <button
          id="scrapeBtn"
          type="submit"
          disabled={isPending}
          className="w-full mt-2 px-6 py-3.5 rounded-xl bg-slate-900 text-white font-bold tracking-wide hover:bg-brand-600 hover:shadow-lg hover:shadow-brand-500/20 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2.5"
        >
          {isPending ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Scraping...</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Fetch Articles</span>
            </>
          )}
        </button>
      </form>

      {isPending && (
        <div className="mt-5">
          <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 transition-all duration-700 ease-out rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-center text-[10px] text-slate-400 mt-2 font-bold uppercase tracking-widest">Retrieving Content</p>
        </div>
      )}

      {state.error && (
        <div className="mt-5 p-4 bg-red-50 border border-red-100 text-red-600 text-sm rounded-xl flex items-start gap-3 animate-fade-in">
          <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <span className="font-medium">{state.error}</span>
        </div>
      )}
    </div>
  )
}

export default ScrapeForm
