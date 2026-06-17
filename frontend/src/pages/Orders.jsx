import { useState, useEffect } from 'react'
import { Plus, Trash2, Edit2, XCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

const statusConfig = {
  Pending:   { label: 'انتظار',   color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  Preparing: { label: 'تحضير',   color: 'bg-blue-100 text-blue-700 border-blue-200' },
  Ready:     { label: 'جاهز',    color: 'bg-green-100 text-green-700 border-green-200' },
  Delivered: { label: 'مُسلَّم', color: 'bg-gray-100 text-gray-500 border-gray-200' },
  Cancelled: { label: 'ملغي',    color: 'bg-red-100 text-red-600 border-red-200' },
}
const nextStatus = { Pending: 'Preparing', Preparing: 'Ready', Ready: 'Delivered' }
const nextLabel  = { Pending: 'ابدأ التحضير', Preparing: 'جاهز للتسليم', Ready: 'تم التسليم' }
const roleAllowed = { Admin: ['Pending','Preparing','Ready'], Chef: ['Pending','Preparing'], Waiter: ['Ready'], Cashier: [] }
const orderTypeLabels = { 'Dine-In': 'داخلي', Takeaway: 'خارجي', Delivery: 'توصيل' }

export default function Orders() {
  const { user } = useAuth()
  const [orders, setOrders]     = useState([])
  const [tables, setTables]     = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [loading, setLoading]   = useState(true)
  const [filter, setFilter]     = useState('all')
  const [expanded, setExpanded] = useState(null)
  const [updating, setUpdating] = useState(null)

  // Add Order Modal
  const [showAdd, setShowAdd]   = useState(false)
  const [addForm, setAddForm]   = useState({ table_id: '', order_type: 'Dine-In', items: [] })
  const [saving, setSaving]     = useState(false)
  const [addError, setAddError] = useState('')

  // Edit Order Modal
  const [editOrder, setEditOrder] = useState(null)
  const [editItems, setEditItems] = useState([])
  const [editSaving, setEditSaving] = useState(false)

  const fetchAll = () => {
    setLoading(true)
    Promise.all([
      axios.get('/api/v1/orders/'),
      axios.get('/api/v1/tables/').catch(() => ({ data: [] })),
      axios.get('/api/v1/menu-items').catch(() => ({ data: [] })),
    ]).then(([ordRes, tabRes, menuRes]) => {
      setOrders(ordRes.data)
      setTables(tabRes.data)
      setMenuItems(menuRes.data.filter(m => m.is_available))
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchAll() }, [])

  /* ── Add Order ── */
  const openAdd = () => {
    setAddForm({ table_id: '', order_type: 'Dine-In', items: [] })
    setAddError('')
    setShowAdd(true)
  }

  const addItemToForm = (menuItem) => {
    setAddForm(f => {
      const ex = f.items.find(i => i.menu_item_id === menuItem.id)
      if (ex) return { ...f, items: f.items.map(i => i.menu_item_id === menuItem.id ? { ...i, quantity: i.quantity + 1 } : i) }
      return { ...f, items: [...f.items, { menu_item_id: menuItem.id, name: menuItem.name, price: menuItem.price, quantity: 1 }] }
    })
  }
  const removeItemFromForm = (id) => {
    setAddForm(f => {
      const ex = f.items.find(i => i.menu_item_id === id)
      if (!ex) return f
      if (ex.quantity === 1) return { ...f, items: f.items.filter(i => i.menu_item_id !== id) }
      return { ...f, items: f.items.map(i => i.menu_item_id === id ? { ...i, quantity: i.quantity - 1 } : i) }
    })
  }

  const submitAdd = async (e) => {
    e.preventDefault()
    if (addForm.items.length === 0) { setAddError('أضف صنفاً واحداً على الأقل'); return }
    setSaving(true); setAddError('')
    try {
      await axios.post('/api/v1/orders/', {
        table_id: addForm.table_id ? parseInt(addForm.table_id) : null,
        order_type: addForm.order_type,
        items: addForm.items.map(i => ({ menu_item_id: i.menu_item_id, quantity: i.quantity })),
      })
      setShowAdd(false)
      fetchAll()
    } catch (err) { setAddError(err.response?.data?.detail || 'حدث خطأ') }
    setSaving(false)
  }

  /* ── Edit Order ── */
  const openEdit = (order) => {
    setEditOrder(order)
    setEditItems(order.order_items?.map(i => ({
      id: i.id,
      menu_item_id: i.menu_item_id,
      name: i.menu_item?.name,
      price: i.ordered_price,
      quantity: i.quantity,
    })) || [])
  }

  const addToEdit = (menuItem) => {
    setEditItems(prev => {
      const ex = prev.find(i => i.menu_item_id === menuItem.id)
      if (ex) return prev.map(i => i.menu_item_id === menuItem.id ? { ...i, quantity: i.quantity + 1 } : i)
      return [...prev, { menu_item_id: menuItem.id, name: menuItem.name, price: menuItem.price, quantity: 1 }]
    })
  }
  const removeFromEdit = (mid) => {
    setEditItems(prev => {
      const ex = prev.find(i => i.menu_item_id === mid)
      if (!ex) return prev
      if (ex.quantity === 1) return prev.filter(i => i.menu_item_id !== mid)
      return prev.map(i => i.menu_item_id === mid ? { ...i, quantity: i.quantity - 1 } : i)
    })
  }

  const submitEdit = async () => {
    if (!editOrder) return
    setEditSaving(true)
    const originalIds = new Set(editOrder.order_items?.map(i => i.menu_item_id) || [])
    const newIds = new Set(editItems.map(i => i.menu_item_id))
    const addItems = editItems.filter(i => !originalIds.has(i.menu_item_id)).map(i => ({ menu_item_id: i.menu_item_id, quantity: i.quantity }))
    const removeIds = (editOrder.order_items || []).filter(i => !newIds.has(i.menu_item_id)).map(i => i.id)
    const updateItems = {}
    editItems.filter(i => originalIds.has(i.menu_item_id)).forEach(i => {
      const orig = editOrder.order_items?.find(o => o.menu_item_id === i.menu_item_id)
      if (orig && orig.quantity !== i.quantity) updateItems[orig.id] = { quantity: i.quantity }
    })
    try {
      await axios.patch(`/api/v1/orders/${editOrder.id}/items`, {
        add_items: addItems,
        update_items: updateItems,
        remove_item_ids: removeIds,
      })
      setEditOrder(null)
      fetchAll()
    } catch {}
    setEditSaving(false)
  }

  /* ── Delete ── */
  const deleteOrder = async (id) => {
    if (!confirm('حذف هذا الطلب؟')) return
    try { await axios.delete(`/api/v1/orders/${id}`); fetchAll() } catch {}
  }

  /* ── Status update ── */
  const updateStatus = async (orderId, newStatus) => {
    setUpdating(orderId)
    try { await axios.patch(`/api/v1/orders/${orderId}/status`, { status: newStatus }); fetchAll() } catch {}
    setUpdating(null)
  }

  const filtered = filter === 'all' ? orders : orders.filter(o => o.status === filter)
  const allowed  = roleAllowed[user?.role] || []
  const canCreate = ['Admin','Waiter'].includes(user?.role)

  if (loading) return <div className="flex items-center justify-center h-full"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>

  return (
    <div className="p-6" dir="rtl">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">الطلبات</h1>
          <p className="text-sm text-gray-500">{orders.length} طلب إجمالي</p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchAll} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200 transition-colors">
            <RefreshCw size={16} /> تحديث
          </button>
          {canCreate && (
            <button onClick={openAdd} className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
              <Plus size={16} /> طلب جديد
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {[['all','الكل'],['Pending','انتظار'],['Preparing','تحضير'],['Ready','جاهز'],['Delivered','مُسلَّم']].map(([v,l]) => (
          <button key={v} onClick={() => setFilter(v)}
            className={`px-3 py-1.5 rounded-xl text-sm font-medium border transition-colors ${filter === v ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Orders Grid */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <XCircle size={40} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 mb-4">لا توجد طلبات</p>
          {canCreate && <button onClick={openAdd} className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-700"><Plus size={16} /> أضف طلباً جديداً</button>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map(order => {
            const s = statusConfig[order.status] || {}
            const next = nextStatus[order.status]
            const canUpdate = allowed.includes(order.status) && next
            const isOpen = expanded === order.id
            const total = order.order_items?.reduce((s, i) => s + i.ordered_price * i.quantity, 0) || 0

            return (
              <div key={order.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="p-4">
                  {/* Title row */}
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-bold text-gray-800">طلب #{order.id}</h3>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {order.table_id ? `طاولة ${order.table_id}` : orderTypeLabels[order.order_type] || 'خارجي'}
                        {' · '}{new Date(order.created_at).toLocaleTimeString('ar', { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-medium border ${s.color}`}>{s.label}</span>
                      {order.status === 'Pending' && (
                        <button onClick={() => openEdit(order)} className="p-1.5 text-blue-500 hover:bg-blue-50 rounded-lg" title="تعديل">
                          <Edit2 size={14} />
                        </button>
                      )}
                      {['Admin'].includes(user?.role) && (
                        <button onClick={() => deleteOrder(order.id)} className="p-1.5 text-red-400 hover:bg-red-50 rounded-lg" title="حذف">
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Items */}
                  <div className="text-sm text-gray-600 mb-3">
                    {order.order_items?.slice(0, isOpen ? undefined : 2).map(item => (
                      <div key={item.id} className="flex justify-between py-1 border-b border-gray-50">
                        <span>{item.menu_item?.name} ×{item.quantity}</span>
                        <span className="text-gray-400">{Number(item.ordered_price * item.quantity).toFixed(2)} ر.س</span>
                      </div>
                    ))}
                    {!isOpen && order.order_items?.length > 2 && (
                      <button onClick={() => setExpanded(order.id)} className="text-blue-500 text-xs mt-1 flex items-center gap-1">
                        <ChevronDown size={14} /> +{order.order_items.length - 2} أصناف
                      </button>
                    )}
                    {isOpen && <button onClick={() => setExpanded(null)} className="text-blue-500 text-xs mt-1 flex items-center gap-1"><ChevronUp size={14} /> إخفاء</button>}
                  </div>

                  {/* Total */}
                  <div className="flex justify-between items-center text-sm font-bold border-t pt-2 mb-2">
                    <span className="text-gray-500">الإجمالي</span>
                    <span className="text-gray-800">{total.toFixed(2)} ر.س</span>
                  </div>

                  {/* Status button */}
                  {canUpdate && (
                    <button onClick={() => updateStatus(order.id, next)} disabled={updating === order.id}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white text-sm py-2 rounded-xl font-medium disabled:opacity-50 transition-colors">
                      {updating === order.id ? '...' : nextLabel[order.status]}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ══ ADD ORDER MODAL ══ */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" dir="rtl">
            <div className="p-5 border-b border-gray-100 flex justify-between items-center">
              <h2 className="text-lg font-bold text-gray-800">إضافة طلب جديد</h2>
              <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600"><XCircle size={22} /></button>
            </div>
            <form onSubmit={submitAdd} className="p-5 space-y-4">
              {addError && <p className="text-red-500 text-sm bg-red-50 p-2 rounded-lg">{addError}</p>}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600 mb-1 block">الطاولة (اختياري)</label>
                  <select value={addForm.table_id} onChange={e => setAddForm(f => ({...f, table_id: e.target.value}))}
                    className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— بدون طاولة —</option>
                    {tables.map(t => <option key={t.id} value={t.id}>طاولة #{t.id} ({t.capacity} أشخاص)</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600 mb-1 block">نوع الطلب</label>
                  <select value={addForm.order_type} onChange={e => setAddForm(f => ({...f, order_type: e.target.value}))}
                    className="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="Dine-In">داخلي</option>
                    <option value="Takeaway">خارجي</option>
                    <option value="Delivery">توصيل</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">اختر الأصناف</label>
                <div className="space-y-1 max-h-48 overflow-y-auto border border-gray-100 rounded-xl p-2">
                  {menuItems.map(item => {
                    const inOrder = addForm.items.find(i => i.menu_item_id === item.id)
                    return (
                      <div key={item.id} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg">
                        <div>
                          <span className="text-sm font-medium text-gray-800">{item.name}</span>
                          <span className="text-xs text-orange-500 mr-2">{Number(item.price).toFixed(2)} ر.س</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {inOrder ? (
                            <>
                              <button type="button" onClick={() => removeItemFromForm(item.id)} className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 hover:bg-gray-200">−</button>
                              <span className="w-6 text-center text-sm font-bold text-blue-600">{inOrder.quantity}</span>
                              <button type="button" onClick={() => addItemToForm(item)} className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 hover:bg-blue-200">+</button>
                            </>
                          ) : (
                            <button type="button" onClick={() => addItemToForm(item)} className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white hover:bg-blue-700">+</button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {addForm.items.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3">
                  <p className="text-xs font-semibold text-blue-700 mb-1">ملخص الطلب:</p>
                  {addForm.items.map(i => (
                    <div key={i.menu_item_id} className="flex justify-between text-sm">
                      <span className="text-gray-700">{i.name} ×{i.quantity}</span>
                      <span className="text-blue-600 font-medium">{(i.price * i.quantity).toFixed(2)} ر.س</span>
                    </div>
                  ))}
                  <div className="border-t border-blue-200 mt-2 pt-1 flex justify-between font-bold text-sm">
                    <span>الإجمالي</span>
                    <span className="text-blue-700">{addForm.items.reduce((s, i) => s + i.price * i.quantity, 0).toFixed(2)} ر.س</span>
                  </div>
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <button type="submit" disabled={saving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'جاري الإضافة...' : 'إضافة الطلب'}
                </button>
                <button type="button" onClick={() => setShowAdd(false)} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl hover:bg-gray-50">إلغاء</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══ EDIT ORDER MODAL ══ */}
      {editOrder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" dir="rtl">
            <div className="p-5 border-b border-gray-100 flex justify-between items-center">
              <h2 className="text-lg font-bold text-gray-800">تعديل طلب #{editOrder.id}</h2>
              <button onClick={() => setEditOrder(null)} className="text-gray-400 hover:text-gray-600"><XCircle size={22} /></button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-2 block">الأصناف</label>
                <div className="space-y-1 max-h-48 overflow-y-auto border border-gray-100 rounded-xl p-2">
                  {menuItems.map(item => {
                    const inEdit = editItems.find(i => i.menu_item_id === item.id)
                    return (
                      <div key={item.id} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded-lg">
                        <div>
                          <span className="text-sm font-medium text-gray-800">{item.name}</span>
                          <span className="text-xs text-orange-500 mr-2">{Number(item.price).toFixed(2)} ر.س</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {inEdit ? (
                            <>
                              <button onClick={() => removeFromEdit(item.id)} className="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200">−</button>
                              <span className="w-6 text-center text-sm font-bold text-blue-600">{inEdit.quantity}</span>
                              <button onClick={() => addToEdit(item)} className="w-7 h-7 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 hover:bg-blue-200">+</button>
                            </>
                          ) : (
                            <button onClick={() => addToEdit(item)} className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white hover:bg-blue-700">+</button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {editItems.length > 0 && (
                <div className="bg-blue-50 rounded-xl p-3">
                  <p className="text-xs font-semibold text-blue-700 mb-1">الطلب المحدَّث:</p>
                  {editItems.map(i => (
                    <div key={i.menu_item_id} className="flex justify-between text-sm">
                      <span className="text-gray-700">{i.name} ×{i.quantity}</span>
                      <span className="text-blue-600 font-medium">{(i.price * i.quantity).toFixed(2)} ر.س</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <button onClick={submitEdit} disabled={editSaving} className="flex-1 bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50">
                  {editSaving ? 'جاري الحفظ...' : 'حفظ التعديلات'}
                </button>
                <button onClick={() => setEditOrder(null)} className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-xl hover:bg-gray-50">إلغاء</button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
