import { useSupabaseStorage } from '../hooks/useSupabaseStorage'

function CacheToggle() {
  const [enabled, setEnabled, , { loading }] = useSupabaseStorage('cache:enabled', true)

  return (
    <div className="flex items-center">
      <label className="flex items-center gap-2.5 cursor-pointer select-none group" htmlFor="cacheToggle">
        <span className={`text-xs font-bold uppercase tracking-wider transition-colors ${enabled ? 'text-brand-600' : 'text-slate-400 group-hover:text-slate-500'}`}>
          Cache
        </span>
        <div className="relative">
          <input
            id="cacheToggle"
            type="checkbox"
            className="sr-only"
            checked={enabled}
            disabled={loading}
            onChange={(e) => setEnabled(e.target.checked)}
          />
          <div className={`w-10 h-6 rounded-full transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] ${enabled ? 'bg-brand-600' : 'bg-slate-200'}`}></div>
          <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full shadow-sm transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] ${enabled ? 'translate-x-4' : 'translate-x-0'}`}></div>
        </div>
      </label>
    </div>
  )
}

export default CacheToggle
