import { useSupabaseStorage } from '../hooks/useSupabaseStorage'
import './CacheToggle.css'

function CacheToggle() {
  const [enabled, setEnabled, , { loading }] = useSupabaseStorage('cache:enabled', true)

  return (
    <div className="cache-toggle-container" data-testid="cache-toggle-container">
      <label className="cache-toggle-label" htmlFor="cacheToggle">
        <input
          id="cacheToggle"
          type="checkbox"
          className="cache-toggle-input"
          data-testid="cache-toggle-input"
          aria-label="Enable cache"
          checked={enabled}
          disabled={loading}
          onChange={(e) => setEnabled(e.target.checked)}
        />
        <span className="cache-toggle-checkbox" data-testid="cache-toggle-switch" />
        <span className="cache-toggle-text">Cache</span>
        <span className="cache-toggle-status" data-testid="cache-toggle-status">
          {enabled ? '(enabled)' : '(disabled)'}
        </span>
      </label>
    </div>
  )
}

export default CacheToggle
