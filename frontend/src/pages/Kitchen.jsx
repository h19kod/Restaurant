import { useState, useEffect, useCallback, useRef } from 'react'
import { ChefHat, Clock, CheckCircle, Bell } from 'lucide-react'
import axios from 'axios'
import { useWebSocket } from '../hooks/useWebSocket'

const statusColors = {
  Pending:   'border-yellow-400 bg-yellow-50',
  Preparing: 'border-blue-400 bg-blue-50',
}

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000)
  if (diff < 60) return `${diff}ث`
  if (diff < 3600) return `${Math.floor(diff / 60)}د`
  return `${Math.floor(diff / 3600)}س`
}

export default function Kitchen() {
  const [orders, setOrders]     = useState([])
  const [loading, setLoading]   = useState(true)
  const [newAlert, setNewAlert] = useState(false)
  const audioRef = useRef(null)

  const fetchOrders = useCallback(async () => {
    try {
      const res = await axios.get('/api/v1/orders/')
      setOrders(res.data.filter(o => ['Pending', 'Preparing'].includes(o.status)))
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchOrders() }, [fetchOrders])

  const onWsMessage = useCallback((msg) => {
    if (msg.event === 'new_order') {
      fetchOrders()
      setNewAlert(true)
      audioRef.current?.play().catch(() => {})
      setTimeout(() => setNewAlert(false), 4000)
    }
  }, [fetchOrders])

  useWebSocket('/ws/kitchen', onWsMessage)

  const updateStatus = async (orderId, newStatus) => {
    try {
      await axios.patch(`/api/v1/orders/${orderId}/status`, { status: newStatus })
      fetchOrders()
    } catch {}
  }

  if (loading) return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center">
      <ChefHat className="text-orange-400 w-12 h-12 animate-bounce" />
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-900 p-4" dir="rtl">
      {/* Header */}
      <div className={`flex items-center justify-between mb-6 p-4 rounded-2xl transition-all duration-500 ${newAlert ? 'bg-orange-500 shadow-lg shadow-orange-500/50' : 'bg-gray-800'}`}>
        <div className="flex items-center gap-3">
          <ChefHat className="text-orange-400 w-8 h-8" />
          <div>
            <h1 className="text-xl font-bold text-white">شاشة المطبخ</h1>
            <p className="text-gray-400 text-sm">{orders.length} طلب نشط</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {newAlert && (
            <div className="flex items-center gap-2 bg-white/20 text-white px-3 py-1.5 rounded-full animate-pulse">
              <Bell className="w-4 h-4" />
              <span className="text-sm font-bold">طلب جديد!</span>
            </div>
          )}
          <div className={`w-3 h-3 rounded-full ${newAlert ? 'bg-white' : 'bg-green-400'} animate-pulse`} title="متصل" />
        </div>
      </div>

      {/* Orders Grid */}
      {orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <CheckCircle className="w-16 h-16 mb-4 text-green-500" />
          <p className="text-xl font-bold text-gray-400">لا توجد طلبات</p>
          <p className="text-sm mt-1">كل الطلبات جاهزة ✅</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {orders.map(order => (
            <div key={order.id}
              className={`rounded-2xl border-2 p-4 shadow-lg ${statusColors[order.status] || 'border-gray-600 bg-gray-800'} transition-all`}>

              {/* Order Header */}
              <div className="flex justify-between items-center mb-3">
                <div>
                  <h2 className="text-2xl font-black text-gray-800">#{order.id}</h2>
                  <p className="text-xs text-gray-500 font-medium">
                    طاولة {order.table_id || '—'}
                  </p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-1 text-gray-500 text-xs">
                    <Clock className="w-3 h-3" />
                    <span>{timeAgo(order.created_at)}</span>
                  </div>
                  <span className={`text-xs font-bold mt-1 block ${order.status === 'Pending' ? 'text-yellow-600' : 'text-blue-600'}`}>
                    {order.status === 'Pending' ? '⏳ انتظار' : '🔥 تحضير'}
                  </span>
                </div>
              </div>

              {/* Items */}
              <div className="space-y-2 mb-4">
                {order.order_items?.map(item => (
                  <div key={item.id} className="flex items-center justify-between bg-white/60 rounded-xl px-3 py-2">
                    <span className="text-sm font-semibold text-gray-800">{item.menu_item?.name}</span>
                    <span className="text-lg font-black text-gray-700 bg-gray-100 w-8 h-8 rounded-full flex items-center justify-center">
                      {item.quantity}
                    </span>
                  </div>
                ))}
              </div>

              {/* Action Button */}
              {order.status === 'Pending' && (
                <button
                  onClick={() => updateStatus(order.id, 'Preparing')}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2.5 rounded-xl transition-colors text-sm"
                >
                  🔥 ابدأ التحضير
                </button>
              )}
              {order.status === 'Preparing' && (
                <button
                  onClick={() => updateStatus(order.id, 'Ready')}
                  className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2.5 rounded-xl transition-colors text-sm"
                >
                  ✅ جاهز للتسليم
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Hidden audio for notification */}
      <audio ref={audioRef} preload="auto">
        <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFhnh0d3+Fh4aDfXZ2fomQjoV8dnB0foiOjIR7c2twfomQj4Z9dG9xfomPjoV9dXByfomRkIiAeHN0fYmQj4Z9dW9yfomRkImBenR1fYmRkImCe3V2f4qSkYqCe3V2f4qTkouDfHZ3gIuTkouEfHd4gIuUk4uEfHh5gYyUlIyFfXl6go2Vlo2GfnqAhI6Xl4+Hf3uBhY+YmJCIgHyCho+ZmZGJgX2Dh5CamZKKgoB/iJGbmpOLg4GAiZKcm5SLhIKBipOdnJaMineBipOdnZaMineBipSenpaMineCi5WfnpeNiHeDi5WgnpeNiXeEjJagn5iOiniFjJehh5mPin6HjZeiiJqPin+IjZiiiZuPioCI" type="audio/wav" />
      </audio>
    </div>
  )
}
