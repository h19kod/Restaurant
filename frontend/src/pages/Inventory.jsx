import { useState, useEffect } from 'react'
import { AlertTriangle, Plus, RefreshCw, PackagePlus } from 'lucide-react'
import axios from 'axios'

export default function Inventory() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [restocking, setRestocking] = useState(null)
  const [restockQty, setRestockQty] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ ingredient_name: '', unit: 'KG', current_stock: '', min_alert_level: '' })
  const [saving, setSaving] = useState(false)

  const fetchItems = () => {
    setLoading(true)
    axios.get('/api/v1/inventory/')
      .then(r => setItems(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchItems() }, [])

  const restock = async (id) => {
    if (!restockQty || isNaN(restockQty)) return
    try {
      await axios.patch(`/api/v1/inventory/${id}/restock`, { quantity_to_add: parseFloat(restockQty) })
      setRestocking(null)
      setRestockQty('')
      fetchItems()
    } catch {}
  }

  const addItem = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await axios.post('/api/v1/inventory/', {
        ...form,
        current_stock: parseFloat(form.current_stock),
        min_alert_level: parseFloat(form.min_alert_level),
      })
      setShowAdd(false)
      setForm({ ingredient_name: '', unit: '', current_stock: '', min_alert_level: '' })
      fetchItems()
    } catch {}
    setSaving(false)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  )

  const lowItems = items.filter(i => i.current_stock <= i.min_alert_level)

  return (
    <div className="p-6" dir="rtl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">المخزون</h1>
          <p className="text-sm text-gray-500">{items.length} صنف · <span className="text-red-500">{lowItems.length} منخفض</span></p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchItems} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
            <RefreshCw size={16} />
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
            <Plus size={16} /> إضافة مادة
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl" dir="rtl">
            <h2 className="text-lg font-bold text-gray-800 mb-4">إضافة مادة للمخزون</h2>
            <form onSubmit={addItem} className="space-y-3">
              <input required placeholder="اسم المادة" value={form.ingredient_name} onChange={e => setForm(f => ({...f, ingredient_name: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <select value={form.unit} onChange={e => setForm(f => ({...f, unit: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="KG">كيلوجرام (KG)</option>
                <option value="Liters">لتر (Liters)</option>
                <option value="Pieces">قطعة (Pieces)</option>
              </select>
              <input required type="number" step="0.01" placeholder="الكمية الحالية" value={form.current_stock} onChange={e => setForm(f => ({...f, current_stock: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input required type="number" step="0.01" placeholder="حد التنبيه الأدنى" value={form.min_alert_level} onChange={e => setForm(f => ({...f, min_alert_level: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? '...' : 'إضافة'}</button>
                <button type="button" onClick={() => setShowAdd(false)} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl hover:bg-gray-50">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {items.map(item => {
          const isLow = item.current_stock <= item.min_alert_level
          const pct = Math.min(100, Math.round((item.current_stock / Math.max(item.min_alert_level * 2, 1)) * 100))
          return (
            <div key={item.id} className={`bg-white rounded-2xl border shadow-sm p-4 ${isLow ? 'border-red-200' : 'border-gray-100'}`}>
              {isLow && (
                <div className="flex items-center gap-1 text-red-500 text-xs font-medium mb-2">
                  <AlertTriangle size={14} /> مخزون منخفض
                </div>
              )}
              <h3 className="font-bold text-gray-800">{item.ingredient_name}</h3>
              <p className="text-2xl font-bold text-gray-700 mt-1">
                {Number(item.current_stock).toFixed(1)} <span className="text-sm text-gray-400">{item.unit}</span>
              </p>
              <div className="mt-2 mb-3">
                <div className="w-full bg-gray-100 rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full ${isLow ? 'bg-red-400' : 'bg-green-400'}`} style={{ width: `${pct}%` }} />
                </div>
                <p className="text-xs text-gray-400 mt-1">حد التنبيه: {item.min_alert_level} {item.unit}</p>
              </div>

              {restocking === item.id ? (
                <div className="flex gap-2 mt-2">
                  <input
                    type="number" step="0.01" placeholder="الكمية"
                    value={restockQty}
                    onChange={e => setRestockQty(e.target.value)}
                    className="flex-1 border border-gray-200 rounded-xl px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button onClick={() => restock(item.id)} className="bg-green-500 text-white px-3 py-1.5 rounded-xl text-sm hover:bg-green-600">✓</button>
                  <button onClick={() => { setRestocking(null); setRestockQty('') }} className="bg-gray-100 text-gray-600 px-3 py-1.5 rounded-xl text-sm">✕</button>
                </div>
              ) : (
                <button onClick={() => setRestocking(item.id)} className="w-full flex items-center justify-center gap-1 text-xs text-blue-600 hover:bg-blue-50 py-1.5 rounded-xl border border-blue-200 transition-colors mt-1">
                  <PackagePlus size={14} /> إعادة تخزين
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
