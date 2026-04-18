import { useEffect, useState } from 'react'

const EMPTY_CART_FORM = {
  person_name: '',
  product_name: '',
}

function formatInputDate(inputDate) {
  const parsedDate = new Date(`${inputDate}T00:00:00Z`)
  return parsedDate.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export default function GroupCartApp() {
  const [cartItems, setCartItems] = useState([])
  const [cartForm, setCartForm] = useState(EMPTY_CART_FORM)
  const [saveState, setSaveState] = useState('idle')
  const [requestError, setRequestError] = useState('')

  async function refreshCartItems() {
    const response = await fetch('/api/shopping-cart/items')
    const payload = await response.json()
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || `HTTP ${response.status}`)
    }

    setCartItems(payload.items)
  }

  useEffect(() => {
    refreshCartItems().catch((error) => {
      setRequestError(error.message)
    })
  }, [])

  async function submitCartItem(event) {
    event.preventDefault()
    setSaveState('saving')
    setRequestError('')

    try {
      const response = await fetch('/api/shopping-cart/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          person_name: cartForm.person_name.trim(),
          product_name: cartForm.product_name.trim(),
        }),
      })
      const payload = await response.json()
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || `HTTP ${response.status}`)
      }

      await refreshCartItems()
      setCartForm(EMPTY_CART_FORM)
      setSaveState('saved')
      window.setTimeout(() => {
        setSaveState((previousState) => (previousState === 'saved' ? 'idle' : previousState))
      }, 1800)
    } catch (error) {
      setSaveState('idle')
      setRequestError(error instanceof Error ? error.message : String(error))
    }
  }

  const saveButtonLabel = saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'Done, saved' : 'Add to cart'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-10">
      <div className="max-w-3xl mx-auto p-4 space-y-4">
        <header className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
          <h1 className="text-lg font-black uppercase tracking-tight">Group Cart</h1>
          <p className="text-sm text-slate-500 mt-1">Shared list for batching purchases and reducing shipping costs.</p>
        </header>

        <form onSubmit={submitCartItem} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <input
            placeholder="Your name"
            required
            value={cartForm.person_name}
            onChange={(event) => setCartForm({ ...cartForm, person_name: event.target.value })}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            placeholder="Product name"
            required
            value={cartForm.product_name}
            onChange={(event) => setCartForm({ ...cartForm, product_name: event.target.value })}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={saveState === 'saving'}
            className="rounded-lg bg-blue-600 text-white font-bold text-sm px-4 py-2 disabled:opacity-60"
          >
            {saveButtonLabel}
          </button>
          {requestError ? <div className="sm:col-span-3 text-sm text-rose-700 font-semibold">{requestError}</div> : null}
        </form>

        <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 text-xs uppercase font-bold text-slate-500">Saved requests</div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm min-w-[520px]">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-2">Day</th>
                  <th className="px-4 py-2">Person</th>
                  <th className="px-4 py-2">Product</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {cartItems.map((cartItem) => (
                  <tr key={cartItem.id}>
                    <td className="px-4 py-2 font-mono text-xs">{formatInputDate(cartItem.input_date)}</td>
                    <td className="px-4 py-2 font-semibold">{cartItem.person_name}</td>
                    <td className="px-4 py-2">{cartItem.product_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {cartItems.length === 0 ? <div className="px-4 py-8 text-sm text-slate-400">No items saved yet.</div> : null}
          </div>
        </section>
      </div>
    </div>
  )
}
