import { AlertTriangle } from 'lucide-react'

export default function Inventory() {
  const items = [
    { name: 'دجاج', stock: 50, unit: 'كجم', min: 20, status: 'ok' },
    { name: 'لحم بقري', stock: 15, unit: 'كجم', min: 20, status: 'low' },
    { name: 'خبز', stock: 100, unit: 'رغيف', min: 50, status: 'ok' },
    { name: 'جبن', stock: 8, unit: 'كجم', min: 10, status: 'low' },
  ]

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-800 mb-8">المخزون</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {items.map((item) => (
          <div
            key={item.name}
            className={`p-6 rounded-xl shadow-md ${
              item.status === 'low' ? 'bg-red-50 border-2 border-red-400' : 'bg-white'
            }`}
          >
            {item.status === 'low' && (
              <div className="flex items-center gap-2 text-red-600 mb-2">
                <AlertTriangle size={18} />
                <span className="text-sm font-medium">نقص في المخزون</span>
              </div>
            )}
            <h3 className="text-xl font-bold text-gray-800">{item.name}</h3>
            <p className="text-3xl font-bold text-gray-700 mt-2">
              {item.stock} <span className="text-lg text-gray-500">{item.unit}</span>
            </p>
            <p className="text-sm text-gray-500 mt-1">الحد الأدنى: {item.min} {item.unit}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
