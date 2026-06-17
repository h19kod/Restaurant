import { useState, useEffect } from 'react'
import { Plus, QrCode, Users, RefreshCw, Copy } from 'lucide-react'
import axios from 'axios'

const statusColors = {
  Empty:    'bg-green-50 border-green-200 text-green-700',
  Occupied: 'bg-red-50 border-red-200 text-red-700',
  Reserved: 'bg-yellow-50 border-yellow-200 text-yellow-700',
}
const statusLabels = { Empty: 'فارغة', Occupied: 'مشغولة', Reserved: 'محجوزة' }

export default function Tables() {
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [capacity, setCapacity] = useState(4)
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState(null)

  const fetchTables = () => {
    setLoading(true)
    axios.get('/api/v1/tables/')
      .then(r => setTables(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchTables() }, [])

  const addTable = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await axios.post('/api/v1/tables/', { capacity: Number(capacity) })
      setShowAdd(false)
      setCapacity(4)
      fetchTables()
    } catch {}
    setSaving(false)
  }

  const copyQrLink = (token) => {
    const url = `${window.location.origin}/order/${token}`
    navigator.clipboard.writeText(url)
    setCopied(token)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  )

  return (
    <div className="p-6" dir="rtl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">الطاولات</h1>
          <p className="text-sm text-gray-500">{tables.length} طاولة</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchTables} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
            <RefreshCw size={16} /> تحديث
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
            <Plus size={16} /> إضافة طاولة
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl" dir="rtl">
            <h2 className="text-lg font-bold text-gray-800 mb-4">إضافة طاولة جديدة</h2>
            <form onSubmit={addTable} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">عدد المقاعد</label>
                <input
                  type="number" min="1" max="20"
                  value={capacity}
                  onChange={e => setCapacity(e.target.value)}
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">
                  {saving ? '...' : 'إضافة'}
                </button>
                <button type="button" onClick={() => setShowAdd(false)} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl font-medium hover:bg-gray-50">
                  إلغاء
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {tables.map(table => {
          const s = statusColors[table.status] || statusColors.Available
          const lbl = statusLabels[table.status] || table.status
          return (
            <div key={table.id} className={`bg-white rounded-2xl border-2 ${s} p-4 text-center shadow-sm`}>
              <div className="text-3xl font-bold text-gray-800 mb-1">#{table.id}</div>
              <div className="flex items-center justify-center gap-1 text-gray-500 text-xs mb-2">
                <Users size={12} /> {table.capacity} أشخاص
              </div>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${s}`}>{lbl}</span>
              {table.qr_code_token && (
                <button
                  onClick={() => copyQrLink(table.qr_code_token)}
                  className="mt-3 w-full flex items-center justify-center gap-1 text-xs text-blue-600 hover:bg-blue-50 py-1.5 rounded-lg border border-blue-200 transition-colors"
                  title="نسخ رابط QR للعميل"
                >
                  {copied === table.qr_code_token ? <><Copy size={12} /> تم النسخ!</> : <><QrCode size={12} /> رابط QR</>}
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
