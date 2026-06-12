import { DollarSign, ShoppingCart, Users, Utensils } from 'lucide-react'

export default function Dashboard() {
  const stats = [
    { label: 'إجمالي المبيعات', value: '12,450 ر.س', icon: DollarSign, color: 'text-green-600 bg-green-100' },
    { label: 'الطلبات اليوم', value: '45', icon: ShoppingCart, color: 'text-blue-600 bg-blue-100' },
    { label: 'العملاء', value: '128', icon: Users, color: 'text-purple-600 bg-purple-100' },
    { label: 'الأصناف', value: '86', icon: Utensils, color: 'text-orange-600 bg-orange-100' },
  ]

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">لوحة التحكم</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div key={stat.label} className="bg-white p-6 rounded-xl shadow-md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm">{stat.label}</p>
                  <p className="text-2xl font-bold text-gray-800 mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.color}`}>
                  <Icon size={28} />
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-8 bg-white p-6 rounded-xl shadow-md">
        <h2 className="text-xl font-bold text-gray-800 mb-4">آخر النشاطات</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-700">طلب جديد #1234</span>
            <span className="text-sm text-gray-500">منذ 5 دقائق</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-700">طلب #1233 جاهز</span>
            <span className="text-sm text-gray-500">منذ 12 دقيقة</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="text-gray-700">تسجيل مستخدم جديد</span>
            <span className="text-sm text-gray-500">منذ 30 دقيقة</span>
          </div>
        </div>
      </div>
    </div>
  )
}
