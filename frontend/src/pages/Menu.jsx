import { useState } from 'react'
import { Plus, Edit, Trash2 } from 'lucide-react'
import axios from 'axios'

export default function Menu() {
  const [categories, setCategories] = useState([])
  const [items, setItems] = useState([])
  const [showModal, setShowModal] = useState(false)

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">القائمة</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          إضافة صنف
        </button>
      </div>
      <div className="bg-white rounded-xl shadow-md p-6">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-right py-3 px-4">الاسم</th>
              <th className="text-right py-3 px-4">التصنيف</th>
              <th className="text-right py-3 px-4">السعر</th>
              <th className="text-right py-3 px-4">الحالة</th>
              <th className="text-right py-3 px-4">الإجراءات</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b hover:bg-gray-50">
              <td className="py-3 px-4">برجر دجاج</td>
              <td className="py-3 px-4">مقبلات</td>
              <td className="py-3 px-4">35 ر.س</td>
              <td className="py-3 px-4"><span className="bg-green-100 text-green-700 px-2 py-1 rounded text-sm">متاح</span></td>
              <td className="py-3 px-4">
                <div className="flex gap-2">
                  <button className="p-2 text-blue-600 hover:bg-blue-50 rounded"><Edit size={18} /></button>
                  <button className="p-2 text-red-600 hover:bg-red-50 rounded"><Trash2 size={18} /></button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
