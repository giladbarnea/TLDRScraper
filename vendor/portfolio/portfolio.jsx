import React, { useMemo, useState, useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from 'recharts'

const CATEGORY_MAP = {
  Mag7: ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA', 'TSLA'],
  'Big Tech+': ['AMD', 'TSM', 'MU', 'SK HYNIX'],
  Experiments: ['CRWV', 'INMD', 'SE', 'TBLA', 'VST', 'HFG GY'],
  Israeli: ['TA-125', 'NAVITAS'],
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', '#14B8A6', '#6366F1', '#84CC16', '#D946EF']

const EMPTY_TRANSACTION_FORM = {
  symbol_id: '',
  transaction_amount_dollars: '',
  shares: '',
}

function categorizeSymbol(symbolId) {
  return Object.keys(CATEGORY_MAP).find((category) => CATEGORY_MAP[category].includes(symbolId)) || 'Bonds'
}

const App = () => {
  const [includeBonds, setIncludeBonds] = useState(false)
  const [activeTab, setActiveTab] = useState('All')
  const [activeIndex, setActiveIndex] = useState(0)
  const [positions, setPositions] = useState([])
  const [transactions, setTransactions] = useState([])
  const [transactionForm, setTransactionForm] = useState(EMPTY_TRANSACTION_FORM)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function refreshPortfolioData() {
    const response = await fetch('/api/portfolio/positions')
    const payload = await response.json()
    if (!response.ok || !payload.success) {
      throw new Error(payload.error || `HTTP ${response.status}`)
    }

    setPositions(payload.positions)
    setTransactions(payload.transactions)
  }

  useEffect(() => {
    refreshPortfolioData()
  }, [])

  const rawData = useMemo(() => {
    const base = positions.reduce((aggregate, position) => {
      if (!includeBonds && position.symbol_id === 'US BONDS 11/34') {
        return aggregate
      }

      aggregate[position.symbol_id] = Number(position.transaction_amount_dollars)
      return aggregate
    }, {})

    const totalValue = Object.values(base).reduce((sum, value) => sum + value, 0)
    if (totalValue === 0) {
      return []
    }

    return Object.entries(base)
      .map(([name, value]) => ({
        name,
        value: Number(value.toFixed(2)),
        p_total: ((value / totalValue) * 100).toFixed(1),
        cat: categorizeSymbol(name),
      }))
      .sort((a, b) => b.value - a.value)
  }, [positions, includeBonds])

  const viewData = useMemo(() => {
    const items = activeTab === 'All' ? rawData : rawData.filter((item) => item.cat === activeTab)
    const viewTotal = items.reduce((sum, item) => sum + item.value, 0)
    return {
      items: items.map((item) => ({
        ...item,
        p_view: viewTotal === 0 ? '0.0' : ((item.value / viewTotal) * 100).toFixed(1),
      })),
      total: viewTotal,
      grandTotal: rawData.reduce((sum, item) => sum + item.value, 0),
    }
  }, [rawData, activeTab])

  useEffect(() => {
    setActiveIndex(0)
  }, [activeTab])

  async function submitTransaction(event) {
    event.preventDefault()
    setIsSubmitting(true)

    try {
      const response = await fetch('/api/portfolio/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol_id: transactionForm.symbol_id.trim(),
          transaction_amount_dollars: Number(transactionForm.transaction_amount_dollars),
          shares: Number(transactionForm.shares),
        }),
      })
      const payload = await response.json()
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || `HTTP ${response.status}`)
      }

      setTransactionForm(EMPTY_TRANSACTION_FORM)
      await refreshPortfolioData()
    } finally {
      setIsSubmitting(false)
    }
  }

  function renderActiveShape(properties) {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, value } = properties
    return (
      <g>
        <text x={cx} y={cy} dy={-8} textAnchor="middle" fill="#1e293b" className="text-base sm:text-lg font-bold">
          {payload.name}
        </text>
        <text x={cx} y={cy} dy={16} textAnchor="middle" fill="#64748b" className="text-xs sm:text-sm font-medium">
          ${value.toLocaleString()}
        </text>
        <Sector
          cx={cx}
          cy={cy}
          innerRadius={innerRadius}
          outerRadius={outerRadius + 6}
          startAngle={startAngle}
          endAngle={endAngle}
          fill={fill}
        />
      </g>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-10">
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto">
          <div className="px-4 py-4 flex justify-between items-center">
            <h1 className="text-lg font-black uppercase tracking-tight">Portfolio</h1>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                <span className="text-[10px] font-bold text-slate-500 uppercase">Bonds</span>
                <input
                  type="checkbox"
                  checked={includeBonds}
                  onChange={(event) => setIncludeBonds(event.target.checked)}
                  className="w-4 h-4 rounded"
                />
              </label>
              <div className="bg-slate-900 text-white px-3 py-1.5 rounded-lg font-mono font-bold text-sm">
                ${viewData.grandTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
          </div>
          <div className="px-4 pb-3 flex gap-2 overflow-x-auto no-scrollbar">
            {['All', ...Object.keys(CATEGORY_MAP), ...(includeBonds ? ['Bonds'] : [])].map((tabName) => (
              <button
                key={tabName}
                onClick={() => setActiveTab(tabName)}
                className={`px-4 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all ${
                  activeTab === tabName ? 'bg-blue-600 text-white shadow-md' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {tabName}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 space-y-4">
        <form onSubmit={submitTransaction} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4 grid grid-cols-1 sm:grid-cols-4 gap-3">
          <input
            placeholder="Symbol ID"
            required
            value={transactionForm.symbol_id}
            onChange={(event) => setTransactionForm({ ...transactionForm, symbol_id: event.target.value })}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            placeholder="Transaction $"
            type="number"
            required
            step="0.01"
            value={transactionForm.transaction_amount_dollars}
            onChange={(event) => setTransactionForm({ ...transactionForm, transaction_amount_dollars: event.target.value })}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <input
            placeholder="Shares"
            type="number"
            required
            step="0.000001"
            value={transactionForm.shares}
            onChange={(event) => setTransactionForm({ ...transactionForm, shares: event.target.value })}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded-lg bg-blue-600 text-white font-bold text-sm px-4 py-2 disabled:opacity-60"
          >
            {isSubmitting ? 'Saving...' : 'Add transaction'}
          </button>
        </form>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
          <div className="h-[300px] sm:h-[400px] w-full">
            {viewData.items.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={280}>
                <PieChart>
                  <Pie
                    activeIndex={activeIndex}
                    activeShape={renderActiveShape}
                    data={viewData.items}
                    cx="50%"
                    cy="50%"
                    innerRadius="65%"
                    outerRadius="85%"
                    dataKey="value"
                    onMouseEnter={(_, index) => setActiveIndex(index)}
                    onClick={(_, index) => setActiveIndex(index)}
                  >
                    {viewData.items.map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} strokeWidth={0} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => `$${value.toLocaleString()}`}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full w-full grid place-items-center text-sm text-slate-400 font-medium">No positions yet</div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse table-fixed sm:table-auto min-w-[320px]">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3 w-[40%] sm:w-auto">Asset</th>
                  <th className="px-4 py-3 text-right">Value</th>
                  <th className="px-2 py-3 text-right">Cat %</th>
                  <th className="px-4 py-3 text-right">Tot %</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {viewData.items.map((item, index) => (
                  <tr
                    key={item.name}
                    onClick={() => setActiveIndex(index)}
                    className={`cursor-pointer transition-colors ${activeIndex === index ? 'bg-blue-50' : 'hover:bg-slate-50'}`}
                  >
                    <td className="px-4 py-4 overflow-hidden text-ellipsis whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                        <span className="text-xs sm:text-sm font-bold truncate">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-xs sm:text-sm">
                      ${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-2 py-4 text-right font-bold text-blue-600 text-[10px] sm:text-xs">{item.p_view}%</td>
                    <td className="px-4 py-4 text-right text-slate-400 text-[10px] sm:text-xs">{item.p_total}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 text-xs uppercase font-bold text-slate-500">Latest transactions</div>
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-xs sm:text-sm">
              <thead className="bg-slate-50 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-2 text-left">Timestamp</th>
                  <th className="px-4 py-2 text-left">Symbol</th>
                  <th className="px-4 py-2 text-right">Amount $</th>
                  <th className="px-4 py-2 text-right">Shares</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {[...transactions].reverse().map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="px-4 py-2 font-mono text-[11px] sm:text-xs">{new Date(transaction.transaction_timestamp).toISOString()}</td>
                    <td className="px-4 py-2 font-semibold">{transaction.symbol_id}</td>
                    <td className="px-4 py-2 text-right font-mono">{Number(transaction.transaction_amount_dollars).toFixed(2)}</td>
                    <td className="px-4 py-2 text-right font-mono">{Number(transaction.shares).toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
