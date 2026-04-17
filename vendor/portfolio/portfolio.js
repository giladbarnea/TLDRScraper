import React, { useMemo, useState, useEffect } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Sector } from 'recharts';

const CATEGORY_MAP = {
  'Mag7': ['AAPL', 'AMZN', 'GOOGL', 'MSFT', 'NVDA', 'TSLA'],
  'Big Tech+': ['AMD', 'TSM', 'MU', 'SK HYNIX'],
  'Experiments': ['CRWV', 'INMD', 'SE', 'TBLA', 'VST', 'HFG GY'],
  'Israeli': ['TA-125', 'NAVITAS']
};

const App = () => {
  const [includeBonds, setIncludeBonds] = useState(false);
  const [activeTab, setActiveTab] = useState('All');
  const [activeIndex, setActiveIndex] = useState(0);

  const rawData = useMemo(() => {
    const rate = 3;
    const base = {
      AAPL: 3175.92,
      AMD: 554.00,
      AMZN: 9237.05,
      CRWV: 2132.64,
      GOOGL: 10101.60 + 5002.50,
      INMD: 7662.90,
      MSFT: 5913.46,
      MU: 1357.08,
      NVDA: 15301.92,
      SE: 273.66,
      TBLA: 7740.90,
      TSM: 4377.72,
      VST: 1663.70,
      TSLA: 1940.50 + (20965.62 / rate),
      'HFG GY': 17683.17 / rate,
      'TA-125': 12000 / rate,
      'NAVITAS': 275.00,
      'SK HYNIX': 4000.00
    };

    if (includeBonds) base['US BONDS 11/34'] = 40000.00;

    const totalValue = Object.values(base).reduce((a, b) => a + b, 0);

    return Object.entries(base).map(([name, value]) => ({
      name,
      value: parseFloat(value.toFixed(2)),
      p_total: ((value / totalValue) * 100).toFixed(1),
      cat: Object.keys(CATEGORY_MAP).find(c => CATEGORY_MAP[c].includes(name)) || 'Bonds'
    })).sort((a, b) => b.value - a.value);
  }, [includeBonds]);

  const viewData = useMemo(() => {
    const items = activeTab === 'All' ? rawData : rawData.filter(d => d.cat === activeTab);
    const vTotal = items.reduce((a, b) => a + b.value, 0);
    return {
      items: items.map(i => ({ ...i, p_view: ((i.value / vTotal) * 100).toFixed(1) })),
      total: vTotal,
      grandTotal: rawData.reduce((a, b) => a + b.value, 0)
    };
  }, [rawData, activeTab]);

  useEffect(() => setActiveIndex(0), [activeTab]);

  const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#F97316', '#14B8A6', '#6366F1', '#84CC16', '#D946EF'];

  const renderActiveShape = (props) => {
    const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill, payload, value } = props;
    return (
      <g>
        <text x={cx} y={cy} dy={-8} textAnchor="middle" fill="#1e293b" className="text-base sm:text-lg font-bold">{payload.name}</text>
        <text x={cx} y={cy} dy={16} textAnchor="middle" fill="#64748b" className="text-xs sm:text-sm font-medium">${value.toLocaleString()}</text>
        <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 6} startAngle={startAngle} endAngle={endAngle} fill={fill} />
      </g>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-10">
      <div className="sticky top-0 z-20 bg-white border-b border-slate-200">
        <div className="max-w-4xl mx-auto">
          <div className="px-4 py-4 flex justify-between items-center">
            <h1 className="text-lg font-black uppercase tracking-tight">Portfolio</h1>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 cursor-pointer bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                <span className="text-[10px] font-bold text-slate-500 uppercase">Bonds</span>
                <input type="checkbox" checked={includeBonds} onChange={e => setIncludeBonds(e.target.checked)} className="w-4 h-4 rounded" />
              </label>
              <div className="bg-slate-900 text-white px-3 py-1.5 rounded-lg font-mono font-bold text-sm">
                ${viewData.grandTotal.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </div>
            </div>
          </div>
          <div className="px-4 pb-3 flex gap-2 overflow-x-auto no-scrollbar">
            {['All', ...Object.keys(CATEGORY_MAP), ...(includeBonds ? ['Bonds'] : [])].map(t => (
              <button key={t} onClick={() => setActiveTab(t)} className={`px-4 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all ${activeTab === t ? 'bg-blue-600 text-white shadow-md' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}>
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-4 space-y-4">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
          <div className="h-[300px] sm:h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie activeIndex={activeIndex} activeShape={renderActiveShape} data={viewData.items} cx="50%" cy="50%" innerRadius="65%" outerRadius="85%" dataKey="value" onMouseEnter={(_, i) => setActiveIndex(i)} onClick={(_, i) => setActiveIndex(i)}>
                  {viewData.items.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} strokeWidth={0} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} formatter={(v) => `$${v.toLocaleString()}`} />
              </PieChart>
            </ResponsiveContainer>
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
                {viewData.items.map((item, i) => (
                  <tr key={item.name} onClick={() => setActiveIndex(i)} className={`cursor-pointer transition-colors ${activeIndex === i ? 'bg-blue-50' : 'hover:bg-slate-50'}`}>
                    <td className="px-4 py-4 overflow-hidden text-ellipsis whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                        <span className="text-xs sm:text-sm font-bold truncate">{item.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-right font-mono text-xs sm:text-sm">${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
                    <td className="px-2 py-4 text-right font-bold text-blue-600 text-[10px] sm:text-xs">{item.p_view}%</td>
                    <td className="px-4 py-4 text-right text-slate-400 text-[10px] sm:text-xs">{item.p_total}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
