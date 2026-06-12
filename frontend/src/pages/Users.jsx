import { Plus, Edit, Trash2 } from 'lucide-react'

export default function Users() {
  const users = [
    { id: 1, name: 'أحمد محمد', username: 'ahmed', role: 'admin', phone: '0501234567' },
    { id: 2, name: 'سارة علي', username: 'sara', role: 'cashier', phone: '0507654321' },
    { id: 3, name: 'خالد سعيد', username: 'khaled', role: 'waiter', phone: '0509876543' },
  ]

  const roleLabels = {
    admin: 'مدير',
    cashier: 'كاشير',
    waiter: 'نادل',
    chef: 'طباخ',
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">المستخدمين</h1>
        <button className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
          <Plus size={20} />
          إضافة مستخدم
        </button>
      </div>
      <div className="bg-white rounded-xl shadow-md p-6">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-right py-3 px-4">الاسم</th>
              <th className="text-right py-3 px-4">اسم المستخدم</th>
              <th className="text-right py-3 px-4">الدور</th>
              <th className="text-right py-3 px-4">الهاتف</th>
              <th className="text-right py-3 px-4">الإجراءات</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="py-3 px-4">{user.name}</td>
                <td className="py-3 px-4">{user.username}</td>
                <td className="py-3 px-4">
                  <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-sm">
                    {roleLabels[user.role]}
                  </span>
                </td>
                <td className="py-3 px-4">{user.phone}</td>
                <td className="py-3 px-4">
                  <div className="flex gap-2">
                    <button className="p-2 text-blue-600 hover:bg-blue-50 rounded"><Edit size={18} /></button>
                    <button className="p-2 text-red-600 hover:bg-red-50 rounded"><Trash2 size={18} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
