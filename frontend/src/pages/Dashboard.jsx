import { useState, useEffect } from 'react'
import { DollarSign, ShoppingCart, LayoutGrid, Utensils, Clock, CheckCircle, AlertTriangle } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

const statusMap = {
  'Pending': { label: 'انتظار', color: 'bg-yellow-100 text-yellow-700' },
  'Preparing': { label: 'تحضير', color: 'bg-blue-100 text-blue-700' },
  'Ready': { label: 'جاهز', color: 'bg-green-100 text-green-700' },
  'Delivered': { label: 'مُسلَّم', color: 'bg-gray-100 text-gray-600' },
  'Cancelled': { label: 'ملغي', color: 'bg-red-100 text-red-600' },
}

export default function Dashboard() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [tables, setTables] = useState([])
  const [menuItems, setMenuItems] = useState([])
  const [lowStock, setLowStock] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      axios.get('/api/v1/orders/').catch(() => ({ data: [] })),
      axios.get('/api/v1/tables/').catch(() => ({ data: [] })),
      axios.get('/api/v1/menu-items').catch(() => ({ data: [] })),
      axios.get('/api/v1/inventory/?low_stock_only=true').catch(() => ({ data: [] })),
    ]).then(([ordersRes, tablesRes, menuRes, stockRes]) => {
      setOrders(ordersRes.data)
      setTables(tablesRes.data)
      setMenuItems(menuRes.data)
      setLowStock(stockRes.data)
    }).finally(() => setLoading(false))
  }, [])

  const activeOrders = orders.filter(o => ['Pending', 'Preparing', 'Ready'].includes(o.status))
  const occupiedTables = tables.filter(t => t.status === 'Occupied').length

  const stats = [
    { label: 'الطلبات النشطة', value: activeOrders.length, icon: ShoppingCart, color: 'text-blue-600 bg-blue-50', border: 'border-blue-200' },
    { label: 'الطاولات المشغولة', value: `${occupiedTables} / ${tables.length}`, icon: LayoutGrid, color: 'text-orange-600 bg-orange-50', border: 'border-orange-200' },
    { label: 'أصناف القائمة', value: menuItems.length, icon: Utensils, color: 'text-purple-600 bg-purple-50', border: 'border-purple-200' },
    { label: 'مخزون منخفض', value: lowStock.length, icon: AlertTriangle, color: 'text-red-600 bg-red-50', border: 'border-red-200' },
  ]

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  )

  return (
    <div className="p-6" dir="rtl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">مرحباً، {user?.full_name} 👋</h1>
        <p className="text-gray-500 text-sm mt-1">هذا ملخص يومك</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className={`bg-white p-5 rounded-2xl border ${stat.border} shadow-sm`}>
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-xl ${stat.color}`}>
                  <Icon size={20} />
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-800">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
            </div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Active Orders */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-base font-bold text-gray-800 mb-4 flex items-center gap-2">
            <Clock size={18} className="text-blue-500" /> الطلبات النشطة
          </h2>
          {activeOrders.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6">لا توجد طلبات نشطة</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {activeOrders.slice(0, 8).map(order => {
                const s = statusMap[order.status] || {}
                return (
                  <div key={order.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <div>
                      <span className="font-semibold text-gray-800 text-sm">طلب #{order.id}</span>
                      {order.table_id && <span className="text-gray-400 text-xs mr-2">طاولة {order.table_id}</span>}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-medium ${s.color}`}>{s.label}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Low Stock Alerts */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-base font-bold text-gray-800 mb-4 flex items-center gap-2">
            <AlertTriangle size={18} className="text-red-500" /> تنبيهات المخزون المنخفض
          </h2>
          {lowStock.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-6 flex flex-col items-center gap-2">
              <CheckCircle size={28} className="text-green-400" />
              المخزون بحالة جيدة
            </p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {lowStock.map(item => (
                <div key={item.id} className="flex items-center justify-between p-3 bg-red-50 rounded-xl">
                  <span className="font-medium text-gray-700 text-sm">{item.ingredient_name}</span>
                  <span className="text-red-600 text-xs font-semibold">{item.current_stock} {item.unit}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
