import { CheckCircle, Clock, XCircle } from 'lucide-react'

export default function Orders() {
  const orders = [
    { id: 1234, table: 5, items: 'برجر دجاج ×2', status: 'pending', time: 'منذ 5 د' },
    { id: 1233, table: 3, items: 'بيتزا ×1', status: 'preparing', time: 'منذ 12 د' },
    { id: 1232, table: 7, items: 'سلطة ×1', status: 'ready', time: 'منذ 20 د' },
  ]

  const statusConfig = {
    pending: { label: 'انتظار', icon: Clock, color: 'bg-yellow-100 text-yellow-700' },
    preparing: { label: 'تحضير', icon: Clock, color: 'bg-blue-100 text-blue-700' },
    ready: { label: 'جاهز', icon: CheckCircle, color: 'bg-green-100 text-green-700' },
    cancelled: { label: 'ملغي', icon: XCircle, color: 'bg-red-100 text-red-700' },
  }

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">الطلبات</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {orders.map((order) => {
          const config = statusConfig[order.status]
          const Icon = config.icon
          return (
            <div key={order.id} className="bg-white rounded-xl shadow-md p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-800">طلب #{order.id}</h3>
                  <p className="text-gray-500">طاولة {order.table}</p>
                </div>
                <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm ${config.color}`}>
                  <Icon size={16} />
                  {config.label}
                </span>
              </div>
              <p className="text-gray-700 mb-4">{order.items}</p>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">{order.time}</span>
                <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                  تفاصيل
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
