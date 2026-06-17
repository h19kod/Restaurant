import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { ShoppingCart, Plus, Minus, ChefHat, CheckCircle, Trash2, UtensilsCrossed } from 'lucide-react'

export default function CustomerOrder() {
  const { qrToken } = useParams()
  const [menuData, setMenuData] = useState(null)
  const [cart, setCart] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [ordered, setOrdered] = useState(false)
  const [orderId, setOrderId] = useState(null)
  const [error, setError] = useState('')
  const [activeCategory, setActiveCategory] = useState(null)
  const [showCart, setShowCart] = useState(false)

  useEffect(() => {
    fetch(`/api/v1/tables/${qrToken}/menu`)
      .then(r => { if (!r.ok) throw new Error('رمز QR غير صالح'); return r.json() })
      .then(data => { setMenuData(data); if (data.categories?.length) setActiveCategory(data.categories[0].id); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [qrToken])

  const addToCart = (item) => {
    setCart(prev => {
      const ex = prev.find(c => c.menu_item_id === item.id)
      if (ex) return prev.map(c => c.menu_item_id === item.id ? { ...c, quantity: c.quantity + 1 } : c)
      return [...prev, { menu_item_id: item.id, name: item.name, price: item.price, quantity: 1 }]
    })
  }

  const removeFromCart = (itemId) => {
    setCart(prev => {
      const ex = prev.find(c => c.menu_item_id === itemId)
      if (!ex) return prev
      if (ex.quantity === 1) return prev.filter(c => c.menu_item_id !== itemId)
      return prev.map(c => c.menu_item_id === itemId ? { ...c, quantity: c.quantity - 1 } : c)
    })
  }

  const deleteFromCart = (itemId) => setCart(prev => prev.filter(c => c.menu_item_id !== itemId))

  const totalQty = cart.reduce((s, c) => s + c.quantity, 0)
  const total = cart.reduce((s, c) => s + c.price * c.quantity, 0)

  const submitOrder = async () => {
    if (cart.length === 0) return
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch('/api/v1/orders/customer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ qr_token: qrToken, items: cart.map(c => ({ menu_item_id: c.menu_item_id, quantity: c.quantity })) })
      })
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || 'فشل إرسال الطلب') }
      const data = await res.json()
      setOrderId(data.id)
      setOrdered(true)
      setCart([])
      setShowCart(false)
    } catch (err) { setError(err.message) }
    setSubmitting(false)
  }

  // Loading
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-orange-50" dir="rtl">
      <div className="text-center">
        <div className="w-20 h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <ChefHat className="w-10 h-10 text-orange-500 animate-bounce" />
        </div>
        <p className="text-gray-500 text-lg">جاري تحميل القائمة...</p>
      </div>
    </div>
  )

  // Error
  if (error && !menuData) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4" dir="rtl">
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-sm w-full text-center">
        <UtensilsCrossed className="w-14 h-14 mx-auto text-red-400 mb-4" />
        <h2 className="text-xl font-bold text-gray-800 mb-2">خطأ في الرابط</h2>
        <p className="text-gray-500 text-sm">{error}</p>
        <p className="text-gray-400 text-xs mt-2">يرجى مسح رمز QR من الطاولة</p>
      </div>
    </div>
  )

  // Success
  if (ordered) return (
    <div className="min-h-screen flex items-center justify-center bg-green-50 p-4" dir="rtl">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-sm w-full text-center">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-12 h-12 text-green-500" />
        </div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">تم استلام طلبك! 🎉</h2>
        <p className="text-gray-500 mb-2">طلبك رقم <span className="font-bold text-orange-500">#{orderId}</span></p>
        <p className="text-gray-400 text-sm mb-6">تم إرسال طلبك للمطبخ، سيصلك قريباً</p>
        <button
          onClick={() => setOrdered(false)}
          className="w-full bg-orange-500 text-white py-3 rounded-xl font-bold text-lg hover:bg-orange-600 transition-colors"
        >
          طلب المزيد 🍽️
        </button>
      </div>
    </div>
  )

  const filteredItems = menuData?.items?.filter(i => i.category_id === activeCategory) || []

  return (
    <div className="min-h-screen bg-gray-50" dir="rtl">
      {/* Header */}
      <div className="bg-gradient-to-l from-orange-500 to-orange-600 text-white sticky top-0 z-20 shadow-md">
        <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <ChefHat className="w-5 h-5" />
              <h1 className="text-lg font-bold">{menuData?.restaurant_name || 'قائمة الطعام'}</h1>
            </div>
            <p className="text-orange-100 text-xs mt-0.5">طاولة #{menuData?.table_id} · {menuData?.table_capacity} أشخاص</p>
          </div>
          <button onClick={() => setShowCart(!showCart)} className="relative p-2">
            <ShoppingCart className="w-7 h-7" />
            {totalQty > 0 && (
              <span className="absolute -top-1 -left-1 bg-white text-orange-500 text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold shadow">
                {totalQty}
              </span>
            )}
          </button>
        </div>

        {/* Category Tabs */}
        <div className="max-w-2xl mx-auto flex overflow-x-auto gap-1 px-4 pb-3 scrollbar-hide">
          {menuData?.categories?.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                activeCategory === cat.id
                  ? 'bg-white text-orange-500 shadow-sm'
                  : 'text-orange-100 hover:bg-orange-400'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="max-w-2xl mx-auto px-4 mt-3">
          <div className="bg-red-50 border border-red-200 text-red-600 p-3 rounded-xl text-sm text-center">{error}</div>
        </div>
      )}

      {/* Cart Drawer */}
      {showCart && (
        <div className="fixed inset-0 z-30 flex flex-col justify-end" onClick={() => setShowCart(false)}>
          <div className="bg-black/40 absolute inset-0" />
          <div className="relative bg-white rounded-t-3xl shadow-2xl p-5 max-h-[75vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <h2 className="text-xl font-bold text-gray-800 mb-4">سلة الطلب</h2>
            {cart.length === 0 ? (
              <p className="text-center text-gray-400 py-8">السلة فارغة</p>
            ) : (
              <>
                <div className="space-y-3 mb-5">
                  {cart.map(item => (
                    <div key={item.menu_item_id} className="flex items-center justify-between bg-gray-50 rounded-xl p-3">
                      <div className="flex-1">
                        <p className="font-medium text-gray-800 text-sm">{item.name}</p>
                        <p className="text-orange-500 text-sm font-bold">{(item.price * item.quantity).toFixed(2)} ر.س</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => removeFromCart(item.menu_item_id)} className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center">
                          <Minus className="w-3 h-3" />
                        </button>
                        <span className="w-5 text-center font-bold text-sm">{item.quantity}</span>
                        <button onClick={() => addToCart({ id: item.menu_item_id, name: item.name, price: item.price })} className="w-7 h-7 rounded-full bg-orange-100 flex items-center justify-center">
                          <Plus className="w-3 h-3 text-orange-600" />
                        </button>
                        <button onClick={() => deleteFromCart(item.menu_item_id)} className="w-7 h-7 rounded-full bg-red-50 flex items-center justify-center mr-1">
                          <Trash2 className="w-3 h-3 text-red-400" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="border-t pt-4">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-gray-500">الإجمالي</span>
                    <span className="text-2xl font-bold text-gray-800">{total.toFixed(2)} ر.س</span>
                  </div>
                  <button
                    onClick={submitOrder}
                    disabled={submitting}
                    className="w-full bg-orange-500 text-white py-4 rounded-2xl font-bold text-lg hover:bg-orange-600 transition-colors disabled:bg-gray-300 shadow-lg"
                  >
                    {submitting ? '⏳ جاري الإرسال...' : `✅ أرسل الطلب (${total.toFixed(2)} ر.س)`}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Menu Items */}
      <div className="max-w-2xl mx-auto px-4 py-4 pb-28 space-y-3">
        {filteredItems.length === 0 ? (
          <p className="text-center text-gray-400 py-16">لا توجد أصناف في هذه الفئة</p>
        ) : filteredItems.map(item => {
          const inCart = cart.find(c => c.menu_item_id === item.id)
          return (
            <div key={item.id} className="bg-white rounded-2xl shadow-sm p-4 flex items-center gap-4">
              <div className="w-16 h-16 bg-gradient-to-br from-orange-100 to-orange-200 rounded-xl flex items-center justify-center flex-shrink-0">
                <span className="text-2xl">🍽️</span>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-bold text-gray-800 text-sm">{item.name}</h3>
                <p className="text-gray-400 text-xs line-clamp-1 mt-0.5">{item.description}</p>
                <p className="text-orange-500 font-bold mt-1">{Number(item.price).toFixed(2)} ر.س</p>
              </div>
              <div className="flex items-center gap-1 flex-shrink-0">
                {inCart ? (
                  <>
                    <button onClick={() => removeFromCart(item.id)} className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center active:scale-95">
                      <Minus className="w-4 h-4 text-gray-600" />
                    </button>
                    <span className="w-7 text-center font-bold text-orange-500">{inCart.quantity}</span>
                    <button onClick={() => addToCart(item)} className="w-8 h-8 rounded-full bg-orange-500 flex items-center justify-center active:scale-95">
                      <Plus className="w-4 h-4 text-white" />
                    </button>
                  </>
                ) : (
                  <button onClick={() => addToCart(item)} className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center shadow-md active:scale-95">
                    <Plus className="w-5 h-5 text-white" />
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Floating Cart Button */}
      {cart.length > 0 && !showCart && (
        <div className="fixed bottom-6 left-4 right-4 z-20 max-w-2xl mx-auto">
          <button
            onClick={() => setShowCart(true)}
            className="w-full bg-orange-500 text-white py-4 rounded-2xl font-bold text-lg shadow-2xl flex items-center justify-between px-6 hover:bg-orange-600 active:scale-[0.98] transition-all"
          >
            <span className="bg-orange-400 px-2.5 py-0.5 rounded-full text-sm">{totalQty}</span>
            <span>عرض الطلب</span>
            <span className="font-bold">{total.toFixed(2)} ر.س</span>
          </button>
        </div>
      )}
    </div>
  )
}
