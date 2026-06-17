import { useState, useEffect } from 'react'
import { Plus, Trash2, RefreshCw, UserCheck, UserX } from 'lucide-react'
import axios from 'axios'

const roleLabels = { Admin: 'مدير', Cashier: 'كاشير', Waiter: 'نادل', Chef: 'طاهي' }
const roleColors = {
  Admin:   'bg-purple-100 text-purple-700',
  Cashier: 'bg-blue-100 text-blue-700',
  Waiter:  'bg-green-100 text-green-700',
  Chef:    'bg-orange-100 text-orange-700',
}

export default function Users() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ username: '', password: '', full_name: '', role: 'Waiter', phone: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchUsers = () => {
    setLoading(true)
    axios.get('/api/v1/users/')
      .then(r => setUsers(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchUsers() }, [])

  const addUser = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await axios.post('/api/v1/auth/register', form)
      setShowAdd(false)
      setForm({ username: '', password: '', full_name: '', role: 'Waiter', phone: '' })
      fetchUsers()
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ')
    }
    setSaving(false)
  }

  const toggleActive = async (user) => {
    try {
      await axios.patch(`/api/v1/users/${user.id}`, { is_active: !user.is_active })
      fetchUsers()
    } catch {}
  }

  const deleteUser = async (id) => {
    if (!confirm('حذف هذا المستخدم؟')) return
    try {
      await axios.delete(`/api/v1/users/${id}`)
      fetchUsers()
    } catch {}
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
          <h1 className="text-2xl font-bold text-gray-800">المستخدمون</h1>
          <p className="text-sm text-gray-500">{users.length} مستخدم</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchUsers} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
            <RefreshCw size={16} />
          </button>
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
            <Plus size={16} /> إضافة مستخدم
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-6 w-full max-w-sm shadow-2xl" dir="rtl">
            <h2 className="text-lg font-bold text-gray-800 mb-4">إضافة مستخدم جديد</h2>
            {error && <p className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded-lg">{error}</p>}
            <form onSubmit={addUser} className="space-y-3">
              <input required placeholder="الاسم الكامل" value={form.full_name} onChange={e => setForm(f => ({...f, full_name: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input required placeholder="اسم المستخدم" value={form.username} onChange={e => setForm(f => ({...f, username: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input required type="password" placeholder="كلمة المرور" value={form.password} onChange={e => setForm(f => ({...f, password: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input placeholder="رقم الهاتف" value={form.phone} onChange={e => setForm(f => ({...f, phone: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <select value={form.role} onChange={e => setForm(f => ({...f, role: e.target.value}))} className="w-full border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="Admin">مدير</option>
                <option value="Cashier">كاشير</option>
                <option value="Waiter">نادل</option>
                <option value="Chef">طاهي</option>
              </select>
              <div className="flex gap-2 pt-2">
                <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">{saving ? '...' : 'إضافة'}</button>
                <button type="button" onClick={() => { setShowAdd(false); setError('') }} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl hover:bg-gray-50">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الاسم</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">اسم المستخدم</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الدور</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الهاتف</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الحالة</th>
              <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">إجراءات</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {users.map(user => (
              <tr key={user.id} className="hover:bg-gray-50 transition-colors">
                <td className="py-3 px-4 font-medium text-gray-800 text-sm">{user.full_name}</td>
                <td className="py-3 px-4 text-gray-500 text-sm">{user.username}</td>
                <td className="py-3 px-4">
                  <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${roleColors[user.role] || 'bg-gray-100 text-gray-600'}`}>
                    {roleLabels[user.role] || user.role}
                  </span>
                </td>
                <td className="py-3 px-4 text-gray-500 text-sm">{user.phone || '—'}</td>
                <td className="py-3 px-4">
                  <button onClick={() => toggleActive(user)} className={`flex items-center gap-1 text-xs font-medium ${user.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                    {user.is_active ? <><UserCheck size={14} /> نشط</> : <><UserX size={14} /> معطل</>}
                  </button>
                </td>
                <td className="py-3 px-4">
                  <button onClick={() => deleteUser(user.id)} className="p-1.5 text-red-500 hover:bg-red-50 rounded-lg transition-colors">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={6} className="text-center py-10 text-gray-400 text-sm">لا يوجد مستخدمون</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
