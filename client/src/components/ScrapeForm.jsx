import { AlertCircle, ArrowRight, Loader2 } from 'lucide-react'
import { useActionState, useState } from 'react'
import { scrapeNewsletters } from '../lib/scraper'

function validateDateRange(startDate, endDate) {
  const startDateObj = new Date(startDate)
  const endDateObj = new Date(endDate)
  const daysDiff = Math.ceil((endDateObj - startDateObj) / (1000 * 60 * 60 * 24))

  if (startDateObj > endDateObj) {
    return { valid: false, error: 'Start date must be before or equal to end date.' }
  }
  if (daysDiff >= 31) {
    return { valid: false, error: 'Date range cannot exceed 31 days.' }
  }
  return { valid: true }
}

function DateInput({ id, label, value, onChange }) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-xs font-bold uppercase tracking-wider text-slate-500">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type="date"
        value={value}
        onChange={onChange}
        required
        className="w-full bg-slate-50 border-0 rounded-lg px-4 py-3 text-slate-900 font-medium focus:ring-2 focus:ring-brand-500 transition-shadow"
      />
    </div>
  )
}

function SubmitButton({ isPending, progress }) {
  return (
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
  )
}

function ProgressBar({ progress }) {
  return (
    <div className="h-1 w-full bg-slate-100 rounded-full overflow-hidden">
      <div
        className="h-full bg-brand-500 transition-all duration-500 ease-out"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}

function ErrorMessage({ message }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-red-50 text-red-600 rounded-xl text-sm">
      <AlertCircle size={18} className="shrink-0 mt-0.5" />
      <p>{message}</p>
    </div>
  )
}

function ScrapeForm({ onResults }) {
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])
  const [startDate, setStartDate] = useState(() => {
    const twoDaysAgo = new Date()
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2)
    return twoDaysAgo.toISOString().split('T')[0]
  })
  const [progress, setProgress] = useState(0)

  const [state, formAction, isPending] = useActionState(
    async (_previousState, formData) => {
      const start = formData.get('start_date')
      const end = formData.get('end_date')

      const validation = validateDateRange(start, end)
      if (!validation.valid) {
        return { error: validation.error }
      }

      setProgress(10)
      const interval = setInterval(() => {
        setProgress(prev => Math.min(prev + 5, 90))
      }, 500)

      try {
        const results = await scrapeNewsletters(start, end)
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
      <h3 className="font-display font-bold text-lg text-slate-900">Sync Settings</h3>

      <form action={formAction} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <DateInput
            id="start_date"
            label="Start Date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <DateInput
            id="end_date"
            label="End Date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>

        <SubmitButton isPending={isPending} progress={progress} />
        {isPending && <ProgressBar progress={progress} />}
      </form>

      {state.error && <ErrorMessage message={state.error} />}
    </div>
  )
}

export default ScrapeForm
