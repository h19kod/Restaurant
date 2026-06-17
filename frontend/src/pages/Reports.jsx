import { useState, useEffect } from 'react'
import { TrendingUp, DollarSign, ShoppingBag, BarChart2, RefreshCw } from 'lucide-react'
import axios from 'axios'

export default function Reports() {
  const [summary, setSummary] = useState(null)
  const [trending, setTrending] = useState([])
  const [range, setRange] = useState('monthly')
  const [loading, setLoading] = useState(true)

  const fetchReports = () => {
    setLoading(true)
    Promise.all([
      axios.get(`/api/v1/reports/sales/summary?range=${range}`).catch(() => ({ data: null })),
      axios.get('/api/v1/reports/items/trending?limit=8').catch(() => ({ data: [] })),
    ]).then(([sumRes, trendRes]) => {
      setSummary(sumRes.data)
      setTrending(trendRes.data || [])
    }).finally(() => setLoading(false))
  }

  useEffect(() => { fetchReports() }, [range])

  const maxQty = trending.length > 0 ? Math.max(...trending.map(t => t.total_quantity_ordered)) : 1

  return (
    <div className="p-6" dir="rtl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">التقارير والتحليلات</h1>
          <p className="text-sm text-gray-500">نظرة عامة على أداء المطعم</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={range}
            onChange={e => setRange(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="daily">اليوم</option>
            <option value="monthly">هذا الشهر</option>
          </select>
          <button onClick={fetchReports} className="flex items-center gap-1 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
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
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-green-50 rounded-xl"><DollarSign size={20} className="text-green-600" /></div>
                  <span className="text-sm text-gray-500">إجمالي الإيرادات</span>
                </div>
                <p className="text-2xl font-bold text-gray-800">{Number(summary.total_revenue).toFixed(2)} ر.س</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-blue-50 rounded-xl"><ShoppingBag size={20} className="text-blue-600" /></div>
                  <span className="text-sm text-gray-500">عدد الفواتير</span>
                </div>
                <p className="text-2xl font-bold text-gray-800">{summary.total_invoices}</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-purple-50 rounded-xl"><TrendingUp size={20} className="text-purple-600" /></div>
                  <span className="text-sm text-gray-500">متوسط قيمة الطلب</span>
                </div>
                <p className="text-2xl font-bold text-gray-800">{Number(summary.average_order_value).toFixed(2)} ر.س</p>
              </div>
            </div>
          )}

          {/* Trending Items */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-base font-bold text-gray-800 mb-4 flex items-center gap-2">
              <BarChart2 size={18} className="text-blue-500" /> الأصناف الأكثر طلباً
            </h2>
            {trending.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-10">لا توجد بيانات بعد — ابدأ باستقبال الطلبات</p>
            ) : (
              <div className="space-y-3">
                {trending.map((item, i) => (
                  <div key={item.menu_item_id}>
                    <div className="flex justify-between items-center mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                        <span className="text-sm font-medium text-gray-700">{item.name}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-gray-400">{item.total_quantity_ordered} طلب</span>
                        <span className="text-sm font-bold text-green-600">{Number(item.total_revenue).toFixed(2)} ر.س</span>
                      </div>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all"
                        style={{ width: `${(item.total_quantity_ordered / maxQty) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
