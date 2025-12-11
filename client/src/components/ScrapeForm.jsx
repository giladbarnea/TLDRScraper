import { AlertCircle, ArrowRight, Loader2 } from 'lucide-react'
import { useActionState, useState } from 'react'
import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import { scrapeNewsletters } from '../lib/scraper'

function ScrapeForm({ onResults }) {
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])
  const [startDate, setStartDate] = useState(() => {
    const twoDaysAgo = new Date()
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2)
    return twoDaysAgo.toISOString().split('T')[0]
  })
  const [cacheEnabled] = useSupabaseStorage('cache:enabled', true)
  const [progress, setProgress] = useState(0)

  const [state, formAction, isPending] = useActionState(
    async (_previousState, formData) => {
      const start = formData.get('start_date')
      const end = formData.get('end_date')

      const startDateObj = new Date(start)
      const endDateObj = new Date(end)
      const daysDiff = Math.ceil((endDateObj - startDateObj) / (1000 * 60 * 60 * 24))

      if (startDateObj > endDateObj) {
        return { error: 'Start date must be before or equal to end date.' }
      }
      if (daysDiff >= 31) {
        return { error: 'Date range cannot exceed 31 days.' }
      }

      setProgress(10)
      const interval = setInterval(() => {
         setProgress(prev => Math.min(prev + 5, 90))
      }, 500)

      try {
        const results = await scrapeNewsletters(start, end, cacheEnabled)
        clearInterval(interval)
        setProgress(100)
        onResults(results)
        return { success: true }
      } catch (err) {
        clearInterval(interval)
        setProgress(0)
        return { error: err.message || 'Network error' }
      }
    },
    { success: false }
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
         <h3 className="font-display font-bold text-lg text-slate-900">Sync Settings</h3>
         <div className="text-xs font-medium text-brand-600 bg-brand-50 px-3 py-1 rounded-full">
            {cacheEnabled ? 'Cache Active' : 'Live Mode'}
         </div>
      </div>

      <form action={formAction} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="start_date" className="block text-xs font-bold uppercase tracking-wider text-slate-500">Start Date</label>
            <input
              id="start_date"
              name="start_date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
              className="w-full bg-slate-50 border-0 rounded-lg px-4 py-3 text-slate-900 font-medium focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="end_date" className="block text-xs font-bold uppercase tracking-wider text-slate-500">End Date</label>
            <input
              id="end_date"
              name="end_date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              required
              className="w-full bg-slate-50 border-0 rounded-lg px-4 py-3 text-slate-900 font-medium focus:ring-2 focus:ring-brand-500 transition-shadow"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isPending}
          className={`
             w-full py-4 rounded-xl font-bold tracking-wide text-sm flex items-center justify-center gap-2 transition-all duration-200
             ${isPending
               ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
               : 'bg-slate-900 text-white hover:bg-brand-600 hover:shadow-lg hover:shadow-brand-500/30'}
          `}
        >
          {isPending ? (
            <>
              <Loader2 className="animate-spin" size={18} />
              <span>Syncing... {progress}%</span>
            </>
          ) : (
            <>
              <span>Update Feed</span>
              <ArrowRight size={18} />
            </>
          )}
        </button>

        {isPending && (
           <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
              <div
                 className="h-full bg-brand-500 transition-all duration-500 ease-out"
                 style={{ width: `${progress}%` }}
              />
           </div>
        )}
      </form>

      {state.error && (
        <div className="flex items-start gap-3 p-4 bg-red-50 text-red-600 rounded-xl text-sm">
           <AlertCircle size={18} className="shrink-0 mt-0.5" />
           <p>{state.error}</p>
        </div>
      )}
    </div>
  )
}

export default ScrapeForm
