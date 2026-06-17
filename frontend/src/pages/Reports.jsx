import { useState, useEffect } from 'react'
import { TrendingUp, DollarSign, ShoppingBag, RefreshCw, BarChart2 } from 'lucide-react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const COLORS = ['#3b82f6','#f97316','#22c55e','#a855f7','#ec4899','#eab308','#06b6d4','#ef4444']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-100 shadow-lg rounded-xl p-3 text-sm" dir="rtl">
      <p className="font-bold text-gray-700 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>{p.name}: <span className="font-bold">{Number(p.value).toFixed(2)}</span></p>
      ))}
    </div>
  )
}

export default function Reports() {
  const [summary, setSummary]   = useState(null)
  const [trending, setTrending] = useState([])
  const [dailySales, setDailySales] = useState([])
  const [range, setRange]       = useState('monthly')
  const [loading, setLoading]   = useState(true)

  const fetchReports = () => {
    setLoading(true)
    const now   = new Date()
    const start = range === 'daily'
      ? new Date(now.setHours(0,0,0,0)).toISOString()
      : new Date(now.getFullYear(), now.getMonth(), 1).toISOString()
    const end   = new Date().toISOString()

    Promise.all([
      axios.get(`/api/v1/reports/sales/summary?range=${range}`).catch(() => ({ data: null })),
      axios.get('/api/v1/reports/items/trending?limit=8').catch(() => ({ data: [] })),
      axios.get(`/api/v1/reports/sales/daily?start=${start}&end=${end}`).catch(() => ({ data: [] })),
    ]).then(([sumRes, trendRes, dailyRes]) => {
      setSummary(sumRes.data)
      setTrending(trendRes.data || [])
      setDailySales((dailyRes.data || []).map(d => ({ date: d.date, revenue: Number(d.revenue), invoices: d.invoice_count })))
    }).finally(() => setLoading(false))
  }

  useEffect(() => { fetchReports() }, [range])

  const pieData = trending.map(t => ({ name: t.name, value: t.total_quantity_ordered }))
  const noData  = trending.length === 0 && dailySales.length === 0

  return (
    <div className="p-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">التقارير والتحليلات</h1>
          <p className="text-sm text-gray-500">نظرة شاملة على أداء المطعم</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={range} onChange={e => setRange(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="daily">اليوم</option>
            <option value="monthly">هذا الشهر</option>
          </select>
          <button onClick={fetchReports} className="flex items-center gap-1 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
        </div>
      ) : (
        <>
          {/* KPI Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {[
                { label: 'إجمالي الإيرادات', value: `${Number(summary.total_revenue).toFixed(2)} ر.س`, icon: DollarSign, color: 'bg-green-50 text-green-600', trend: '+' },
                { label: 'عدد الفواتير',     value: summary.total_invoices,                             icon: ShoppingBag, color: 'bg-blue-50 text-blue-600' },
                { label: 'متوسط الطلب',      value: `${Number(summary.average_order_value).toFixed(2)} ر.س`, icon: TrendingUp, color: 'bg-purple-50 text-purple-600' },
              ].map(({ label, value, icon: Icon, color }) => (
                <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`p-2 rounded-xl ${color}`}><Icon size={20} /></div>
                    <span className="text-sm text-gray-500">{label}</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-800">{value}</p>
                </div>
              ))}
            </div>
          )}

          {noData ? (
            <div className="bg-white rounded-2xl border border-gray-100 p-16 text-center">
              <BarChart2 size={40} className="mx-auto text-gray-300 mb-3" />
              <p className="text-gray-400">لا توجد بيانات بعد — ابدأ باستقبال الطلبات وإصدار الفواتير</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

              {/* Bar Chart — Daily Revenue */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <h2 className="text-base font-bold text-gray-800 mb-4">الإيرادات اليومية</h2>
                {dailySales.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-10">لا توجد بيانات للفترة المحددة</p>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={dailySales} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={d => d.slice(5)} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="revenue" name="الإيرادات (ر.س)" fill="#3b82f6" radius={[6,6,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Pie Chart — Trending Items */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <h2 className="text-base font-bold text-gray-800 mb-4">توزيع الأصناف المطلوبة</h2>
                {pieData.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-10">لا توجد طلبات بعد</p>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" outerRadius={85} dataKey="value" nameKey="name" label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`} labelLine={false}>
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => [`${v} طلب`, 'الكمية']} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>

              {/* Top Items Table */}
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 xl:col-span-2">
                <h2 className="text-base font-bold text-gray-800 mb-4">الأصناف الأكثر مبيعاً</h2>
                <div className="space-y-3">
                  {trending.map((item, i) => (
                    <div key={item.menu_item_id}>
                      <div className="flex justify-between items-center mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: COLORS[i % COLORS.length] }}>{i+1}</span>
                          <span className="text-sm font-medium text-gray-700">{item.name}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-xs text-gray-400">{item.total_quantity_ordered} طلب</span>
                          <span className="text-sm font-bold text-green-600">{Number(item.total_revenue).toFixed(2)} ر.س</span>
                        </div>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div className="h-2 rounded-full transition-all" style={{
                          width: `${(item.total_quantity_ordered / Math.max(...trending.map(t => t.total_quantity_ordered))) * 100}%`,
                          background: COLORS[i % COLORS.length]
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          )}
        </>
      )}
    </div>
  )
}
