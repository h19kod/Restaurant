import { useState, useEffect, useCallback } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js'
import { Receipt, CreditCard, Banknote, Tag, CheckCircle, RefreshCw, XCircle, Download } from 'lucide-react'
import { generateInvoicePDF } from '../utils/generatePDF'
import axios from 'axios'

const stripeKey = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY
const stripePromise = stripeKey ? loadStripe(stripeKey) : null

// ── Stripe Card Form ──────────────────────────────────────────────────────────
function StripeForm({ orderId, couponCode, onSuccess, onCancel }) {
  const stripe  = useStripe()
  const elements = useElements()
  const [msg, setMsg]   = useState('')
  const [busy, setBusy] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!stripe || !elements) return
    setBusy(true)
    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: window.location.href },
      redirect: 'if_required',
    })
    if (error) {
      setMsg(error.message)
      setBusy(false)
    } else {
      await axios.post(`/api/v1/billing/invoices/settle/${orderId}`, {
        payment_method: 'Card',
        coupon_code: couponCode || null,
      })
      onSuccess()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <PaymentElement />
      {msg && <p className="text-red-500 text-sm bg-red-50 p-2 rounded-lg">{msg}</p>}
      <div className="flex gap-2">
        <button type="submit" disabled={busy || !stripe}
          className="flex-1 bg-purple-600 text-white py-3 rounded-xl font-bold hover:bg-purple-700 disabled:opacity-50">
          {busy ? '⏳ جاري الدفع...' : '💳 ادفع بالبطاقة'}
        </button>
        <button type="button" onClick={onCancel}
          className="flex-1 border border-gray-200 text-gray-600 py-3 rounded-xl hover:bg-gray-50">
          إلغاء
        </button>
      </div>
    </form>
  )
}

// ── Invoice Modal ─────────────────────────────────────────────────────────────
function InvoiceModal({ order, onClose, onPaid }) {
  const [preview, setPreview] = useState(null)
  const [coupon, setCoupon]   = useState('')
  const [couponInput, setCouponInput] = useState('')
  const [loadingPreview, setLoadingPreview] = useState(true)
  const [paying, setPaying]   = useState(false)
  const [clientSecret, setClientSecret] = useState(null)
  const [stripeOpts, setStripeOpts] = useState(null)
  const [paid, setPaid]       = useState(false)
  const [error, setError]     = useState('')

  const fetchPreview = useCallback(async (code) => {
    setLoadingPreview(true)
    try {
      const params = code ? `?coupon_code=${code}` : ''
      const res = await axios.post(`/api/v1/billing/invoices/preview/${order.id}${params}`)
      setPreview(res.data)
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'خطأ في تحميل الفاتورة')
    }
    setLoadingPreview(false)
  }, [order.id])

  useEffect(() => { fetchPreview('') }, [fetchPreview])

  const applyCoupon = () => { setCoupon(couponInput); fetchPreview(couponInput) }

  const payByCash = async () => {
    setPaying(true)
    try {
      await axios.post(`/api/v1/billing/invoices/settle/${order.id}`, {
        payment_method: 'Cash',
        coupon_code: coupon || null,
      })
      setPaid(true)
    } catch (err) { setError(err.response?.data?.detail || 'حدث خطأ') }
    setPaying(false)
  }

  const payByCard = async () => {
    if (!stripePromise) { setError('Stripe غير مفعّل — أضف VITE_STRIPE_PUBLISHABLE_KEY في .env'); return }
    setPaying(true)
    try {
      const params = coupon ? `?coupon_code=${coupon}` : ''
      const res = await axios.post(`/api/v1/billing/payment-intent/${order.id}${params}`)
      setClientSecret(res.data.client_secret)
      setStripeOpts({ clientSecret: res.data.client_secret })
    } catch (err) { setError(err.response?.data?.detail || 'خطأ في Stripe') }
    setPaying(false)
  }

  if (paid) return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" dir="rtl">
      <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle className="w-10 h-10 text-green-500" />
        </div>
        <h2 className="text-xl font-bold text-gray-800 mb-2">تم الدفع بنجاح! ✅</h2>
        <p className="text-gray-500 text-sm mb-2">فاتورة طلب #{order.id}</p>
        <p className="text-2xl font-bold text-green-600 mb-6">{Number(preview?.total_amount || 0).toFixed(2)} ر.س</p>
        <button onClick={() => { onPaid(); onClose() }}
          className="w-full bg-green-500 text-white py-3 rounded-xl font-bold hover:bg-green-600">
          إغلاق
        </button>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" dir="rtl">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="p-5 border-b border-gray-100 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-gray-800">فاتورة طلب #{order.id}</h2>
            <p className="text-xs text-gray-400">طاولة #{order.table_id || '—'}</p>
          </div>
          <button onClick={onClose}><XCircle className="text-gray-400" size={22} /></button>
        </div>

        <div className="p-5 space-y-4">
          {error && <p className="text-red-500 text-sm bg-red-50 p-2 rounded-lg">{error}</p>}

          {/* Order Items */}
          <div className="bg-gray-50 rounded-xl p-3 space-y-1">
            {order.order_items?.map(item => (
              <div key={item.id} className="flex justify-between text-sm">
                <span className="text-gray-700">{item.menu_item?.name} ×{item.quantity}</span>
                <span className="text-gray-500">{Number(item.ordered_price * item.quantity).toFixed(2)} ر.س</span>
              </div>
            ))}
          </div>

          {/* Coupon */}
          <div className="flex gap-2">
            <input
              value={couponInput}
              onChange={e => setCouponInput(e.target.value)}
              placeholder="كود الخصم (اختياري)"
              className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button onClick={applyCoupon} className="flex items-center gap-1 bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded-xl text-sm font-medium">
              <Tag size={14} /> تطبيق
            </button>
          </div>

          {/* Totals */}
          {loadingPreview ? (
            <div className="flex justify-center py-4"><div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600" /></div>
          ) : preview && (
            <div className="border border-gray-100 rounded-xl p-3 space-y-1.5">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">المجموع الفرعي</span>
                <span>{Number(preview.subtotal).toFixed(2)} ر.س</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">الضريبة (15%)</span>
                <span>{Number(preview.tax_amount).toFixed(2)} ر.س</span>
              </div>
              {preview.coupon_applied && (
                <div className="flex justify-between text-sm text-green-600">
                  <span>خصم الكوبون 🎉</span>
                  <span>−{Number(preview.discount_amount).toFixed(2)} ر.س</span>
                </div>
              )}
              <div className="flex justify-between font-bold text-base border-t pt-2 mt-1">
                <span>الإجمالي</span>
                <span className="text-blue-700 text-lg">{Number(preview.total_amount).toFixed(2)} ر.س</span>
              </div>
            </div>
          )}

          {/* Payment Buttons or Stripe Form */}
          {clientSecret && stripeOpts ? (
            <Elements stripe={stripePromise} options={stripeOpts}>
              <StripeForm
                orderId={order.id}
                couponCode={coupon}
                onSuccess={() => setPaid(true)}
                onCancel={() => { setClientSecret(null); setStripeOpts(null) }}
              />
            </Elements>
          ) : (
            <div className="grid grid-cols-2 gap-3 pt-1">
              <button onClick={payByCash} disabled={paying || loadingPreview}
                className="flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-bold disabled:opacity-50 transition-colors">
                <Banknote size={18} /> نقداً
              </button>
              <button onClick={payByCard} disabled={paying || loadingPreview}
                className="flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white py-3 rounded-xl font-bold disabled:opacity-50 transition-colors">
                <CreditCard size={18} /> بطاقة
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main Billing Page ─────────────────────────────────────────────────────────
export default function Billing() {
  const [orders, setOrders]     = useState([])
  const [invoices, setInvoices] = useState([])
  const [loading, setLoading]   = useState(true)
  const [selected, setSelected] = useState(null)
  const [tab, setTab]           = useState('pending')

  const fetchAll = () => {
    setLoading(true)
    Promise.all([
      axios.get('/api/v1/orders/'),
      axios.get('/api/v1/billing/invoices').catch(() => ({ data: [] })),
    ]).then(([ordRes, invRes]) => {
      setOrders(ordRes.data)
      setInvoices(invRes.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchAll() }, [])

  const settledOrderIds = new Set(invoices.map(i => i.order_id))
  const pendingOrders   = orders.filter(o => !settledOrderIds.has(o.id) && o.status !== 'Cancelled')
  const paidOrders      = invoices

  const totalRevenue = invoices.reduce((s, i) => s + Number(i.total_amount), 0)

  if (loading) return <div className="flex items-center justify-center h-full"><div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" /></div>

  return (
    <div className="p-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">الفوترة والدفع</h1>
          <p className="text-sm text-gray-500">إجمالي الإيرادات: <span className="font-bold text-green-600">{totalRevenue.toFixed(2)} ر.س</span></p>
        </div>
        <button onClick={fetchAll} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200">
          <RefreshCw size={16} /> تحديث
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-5">
        {[['pending', `طلبات بانتظار الدفع (${pendingOrders.length})`], ['paid', `فواتير مدفوعة (${paidOrders.length})`]].map(([v,l]) => (
          <button key={v} onClick={() => setTab(v)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${tab === v ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`}>
            {l}
          </button>
        ))}
      </div>

      {/* Pending Orders */}
      {tab === 'pending' && (
        pendingOrders.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <CheckCircle className="mx-auto text-green-300 mb-3" size={40} />
            <p className="text-gray-400">جميع الطلبات تمت تسويتها ✅</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {pendingOrders.map(order => {
              const total = order.order_items?.reduce((s, i) => s + Number(i.ordered_price) * i.quantity, 0) || 0
              const statusColors = { Pending: 'text-yellow-600 bg-yellow-50', Preparing: 'text-blue-600 bg-blue-50', Ready: 'text-green-600 bg-green-50', Delivered: 'text-gray-600 bg-gray-50' }
              const statusLabels = { Pending: 'انتظار', Preparing: 'تحضير', Ready: 'جاهز', Delivered: 'مُسلَّم' }
              return (
                <div key={order.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-bold text-gray-800">طلب #{order.id}</h3>
                      <p className="text-xs text-gray-400">طاولة #{order.table_id || '—'} · {order.order_items?.length} صنف</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${statusColors[order.status] || 'bg-gray-50 text-gray-600'}`}>
                      {statusLabels[order.status] || order.status}
                    </span>
                  </div>
                  <div className="space-y-1 mb-3">
                    {order.order_items?.slice(0, 3).map(i => (
                      <div key={i.id} className="flex justify-between text-xs text-gray-500">
                        <span>{i.menu_item?.name} ×{i.quantity}</span>
                        <span>{Number(i.ordered_price * i.quantity).toFixed(2)}</span>
                      </div>
                    ))}
                    {order.order_items?.length > 3 && <p className="text-xs text-gray-400">+{order.order_items.length - 3} أصناف أخرى</p>}
                  </div>
                  <div className="flex justify-between items-center border-t pt-2 mb-3">
                    <span className="text-xs text-gray-400">الإجمالي التقديري</span>
                    <span className="font-bold text-gray-700">{total.toFixed(2)} ر.س</span>
                  </div>
                  <button onClick={() => setSelected(order)}
                    className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-xl font-medium text-sm transition-colors">
                    <Receipt size={16} /> إصدار فاتورة ودفع
                  </button>
                </div>
              )
            })}
          </div>
        )
      )}

      {/* Paid Invoices */}
      {tab === 'paid' && (
        paidOrders.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <Receipt className="mx-auto text-gray-300 mb-3" size={40} />
            <p className="text-gray-400">لا توجد فواتير بعد</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">رقم الفاتورة</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الطلب</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">المجموع</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الضريبة</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">الإجمالي</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">طريقة الدفع</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500">التاريخ</th>
                  <th className="py-3 px-4"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {paidOrders.map(inv => (
                  <tr key={inv.id} className="hover:bg-gray-50">
                    <td className="py-3 px-4 text-sm font-medium text-gray-800">#{inv.id}</td>
                    <td className="py-3 px-4 text-sm text-gray-500">طلب #{inv.order_id}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">{Number(inv.subtotal).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm text-gray-600">{Number(inv.tax_amount).toFixed(2)}</td>
                    <td className="py-3 px-4 text-sm font-bold text-green-600">{Number(inv.total_amount).toFixed(2)} ر.س</td>
                    <td className="py-3 px-4">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${inv.payment_method === 'Cash' ? 'bg-green-50 text-green-600' : inv.payment_method === 'Card' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'}`}>
                        {inv.payment_method === 'Cash' ? '💵 نقداً' : inv.payment_method === 'Card' ? '💳 بطاقة' : '🌐 أونلاين'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-400">
                      {new Date(inv.paid_at).toLocaleDateString('ar', { day: '2-digit', month: 'short', year: 'numeric' })}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => {
                          const order = orders.find(o => o.id === inv.order_id)
                          generateInvoicePDF(inv, order)
                        }}
                        className="flex items-center gap-1 text-xs text-blue-600 hover:bg-blue-50 px-2 py-1 rounded-lg"
                      >
                        <Download size={12} /> PDF
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {/* Invoice Modal */}
      {selected && (
        <InvoiceModal
          order={selected}
          onClose={() => setSelected(null)}
          onPaid={fetchAll}
        />
      )}
    </div>
  )
}
