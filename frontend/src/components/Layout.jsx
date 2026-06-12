import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Home, Utensils, ClipboardList, LayoutGrid, Package, BarChart3, Users, LogOut } from 'lucide-react'

const menuItems = [
  { path: '/dashboard', icon: Home, label: 'الرئيسية' },
  { path: '/menu', icon: Utensils, label: 'القائمة' },
  { path: '/orders', icon: ClipboardList, label: 'الطلبات' },
  { path: '/tables', icon: LayoutGrid, label: 'الطاولات' },
  { path: '/inventory', icon: Package, label: 'المخزون' },
  { path: '/reports', icon: BarChart3, label: 'التقارير' },
  { path: '/users', icon: Users, label: 'المستخدمين' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <div className="flex h-screen bg-gray-100">
      <aside className="w-64 bg-white shadow-lg">
        <div className="p-6 border-b">
          <h1 className="text-2xl font-bold text-gray-800">نظام المطاعم</h1>
          <p className="text-sm text-gray-500 mt-1">{user?.full_name}</p>
        </div>
        <nav className="p-4">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-2 transition-colors ${
                  isActive ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
        <div className="absolute bottom-0 w-64 p-4 border-t bg-white">
          <button
            onClick={logout}
            className="flex items-center gap-3 px-4 py-3 text-red-600 hover:bg-red-50 rounded-lg w-full"
          >
            <LogOut size={20} />
            <span>تسجيل خروج</span>
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
