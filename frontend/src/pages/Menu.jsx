import { useState, useEffect } from 'react'
import { Plus, Trash2, ToggleLeft, ToggleRight, RefreshCw } from 'lucide-react'
import axios from 'axios'

export default function Menu() {
  const [categories, setCategories] = useState([])
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', price: '', category_id: '', is_available: true })
  const [saving, setSaving] = useState(false)
  const [activeCategory, setActiveCategory] = useState('all')

  const fetchData = () => {
    setLoading(true)
    Promise.all([
      axios.get('/api/v1/categories'),
      axios.get('/api/v1/menu-items'),
    ]).then(([catRes, itemRes]) => {
      setCategories(catRes.data)
      setItems(itemRes.data)
      if (catRes.data.length > 0 && activeCategory === 'all') setActiveCategory('all')
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchData() }, [])

  const addItem = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await axios.post('/api/v1/menu-items', {
        ...form,
        price: parseFloat(form.price),
        category_id: parseInt(form.category_id),
      })
      setShowAdd(false)
      setForm({ name: '', description: '', price: '', category_id: '', is_available: true })
      fetchData()
    } catch {}
    setSaving(false)
  }

  const toggleAvailable = async (item) => {
    try {
      await axios.patch(`/api/v1/menu-items/${item.id}`, { is_available: !item.is_available })
      fetchData()
    } catch {}
  }

  const deleteItem = async (id) => {
    if (!confirm('حذف هذا الصنف؟')) return
    try {
      await axios.delete(`/api/v1/menu-items/${id}`)
      fetchData()
    } catch {}
  }

  const filtered = activeCategory === 'all' ? items : items.filter(i => i.category_id === activeCategory)

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  )

  return (
    <div className="p-6" dir="rtl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">قائمة الطعام</h1>
          <p className="text-sm text-gray-500">{items.length} صنف</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchData} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
            <RefreshCw size={16} />
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
            <Plus size={16} /> إضافة صنف
          </button>
        </div>
      </div>

      {/* Category filter */}
      <div className="flex gap-2 mb-5 overflow-x-auto pb-1">
        <button onClick={() => setActiveCategory('all')} className={`px-3 py-1.5 rounded-xl text-sm font-medium border whitespace-nowrap transition-colors ${activeCategory === 'all' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'}`}>
          الكل
        </button>
        {categories.map(c => (
          <button key={c.id} onClick={() => setActiveCategory(c.id)} className={`px-3 py-1.5 rounded-xl text-sm font-medium border whitespace-nowrap transition-colors ${activeCategory === c.id ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200'}`}>
            {c.name}
          </button>
        ))}
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl" dir="rtl">
            <h2 className="text-lg font-bold text-gray-800 mb-4">إضافة صنف جديد</h2>
            <form onSubmit={addItem} className="space-y-3">
              <input required placeholder="اسم الصنف" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input placeholder="الوصف" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input required type="number" step="0.01" placeholder="السعر (ر.س)" value={form.price} onChange={e => setForm(f => ({...f, price: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <select required value={form.category_id} onChange={e => setForm(f => ({...f, category_id: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="">اختر التصنيف</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? '...' : 'إضافة'}</button>
                <button type="button" onClick={() => setShowAdd(false)} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl hover:bg-gray-50">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Items Table */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">الصنف</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">التصنيف</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">السعر</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">الحالة</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">إجراءات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.map(item => (
              <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                <td className="py-3 px-4">
                  <div>
                    <p className="font-medium text-gray-800 text-sm">{item.name}</p>
                    {item.description && <p className="text-xs text-gray-400 mt-0.5">{item.description}</p>}
                  </div>
                </td>
                <td className="py-3 px-4 text-sm text-gray-600">{item.category?.name || '—'}</td>
                <td className="py-3 px-4 text-sm font-semibold text-gray-800">{Number(item.price).toFixed(2)} ر.س</td>
                <td className="py-3 px-4">
                  <button onClick={() => toggleAvailable(item)} className="flex items-center gap-1 text-xs font-medium">
                    {item.is_available
                      ? <><ToggleRight size={20} className="text-green-500" /><span className="text-green-600">متاح</span></>
                      : <><ToggleLeft size={20} className="text-gray-400" /><span className="text-gray-400">غير متاح</span></>
                    }
                  </button>
                </td>
                <td className="py-3 px-4">
                  <button onClick={() => deleteItem(item.id)} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={5} className="text-center py-10 text-gray-400 text-sm">لا توجد أصناف</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
