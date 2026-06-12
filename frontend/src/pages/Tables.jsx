import { Plus } from 'lucide-react'

export default function Tables() {
  const tables = [
    { id: 1, number: 1, capacity: 4, status: 'occupied' },
    { id: 2, number: 2, capacity: 4, status: 'empty' },
    { id: 3, number: 3, capacity: 6, status: 'occupied' },
    { id: 4, number: 4, capacity: 2, status: 'empty' },
    { id: 5, number: 5, capacity: 8, status: 'empty' },
  ]

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">الطاولات</h1>
        <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={20} />
          إضافة طاولة
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {tables.map((table) => (
          <div
            key={table.id}
            className={`p-6 rounded-xl text-center cursor-pointer transition-all ${
              table.status === 'occupied' ? 'bg-red-100 border-2 border-red-400' : 'bg-green-100 border-2 border-green-400'
            }`}
          >
            <h3 className="text-3xl font-bold text-gray-800">{table.number}</h3>
            <p className="text-gray-600 mt-2">{table.capacity} أشخاص</p>
            <p className={`mt-2 font-medium ${table.status === 'occupied' ? 'text-red-600' : 'text-green-600'}`}>
              {table.status === 'occupied' ? 'مشغولة' : 'فارغة'}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
