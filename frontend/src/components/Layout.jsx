import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useI18n } from '../context/i18n'
import { Home, Utensils, ClipboardList, LayoutGrid, Package, BarChart3, Users, LogOut, ChefHat, Receipt, Languages, Monitor, CreditCard } from 'lucide-react'

const allNavItems = [
  { path: '/dashboard', icon: Home, label: 'الرئيسية', roles: ['Admin', 'Cashier', 'Waiter', 'Chef'] },
  { path: '/orders', icon: ClipboardList, label: 'الطلبات', roles: ['Admin', 'Cashier', 'Waiter', 'Chef'] },
  { path: '/tables', icon: LayoutGrid, label: 'الطاولات', roles: ['Admin', 'Waiter'] },
  { path: '/menu', icon: Utensils, label: 'القائمة', roles: ['Admin'] },
  { path: '/inventory', icon: Package, label: 'المخزون', roles: ['Admin', 'Chef'] },
  { path: '/kitchen', icon: Monitor, label: 'شاشة المطبخ', roles: ['Admin', 'Chef'] },
  { path: '/billing', icon: Receipt, label: 'الفوترة والدفع', roles: ['Admin', 'Cashier'] },
  { path: '/reports', icon: BarChart3, label: 'التقارير', roles: ['Admin', 'Cashier'] },
  { path: '/users', icon: Users, label: 'المستخدمين', roles: ['Admin'] },
  { path: '/subscription', icon: CreditCard, label: 'الاشتراك', roles: ['Admin'] },
]

const roleColors = {
  Admin: 'bg-purple-100 text-purple-700',
  Cashier: 'bg-blue-100 text-blue-700',
  Waiter: 'bg-green-100 text-green-700',
  Chef: 'bg-orange-100 text-orange-700',
}

const roleLabels = {
  Admin: 'مدير',
  Cashier: 'كاشير',
  Waiter: 'نادل',
  Chef: 'طاهي',
}

export default function Layout() {
  const { user, logout } = useAuth()
  const { lang, toggleLang, t } = useI18n()
  const location = useLocation()

  const navItems = allNavItems.filter(item =>
    !user?.role || item.roles.includes(user.role)
  )

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden" dir={lang === 'ar' ? 'rtl' : 'ltr'}>
      {/* Sidebar */}
      <aside className="w-64 bg-white border-l border-gray-200 flex flex-col shadow-sm">
        {/* Logo */}
        <div className="p-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
              <ChefHat className="text-white" size={20} />
            </div>
            <div>
              <h1 className="text-base font-bold text-gray-800">نظام المطاعم</h1>
              <p className="text-xs text-gray-500">لوحة التحكم</p>
            </div>
          </div>
        </div>

        {/* User Info */}
        <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <p className="text-sm font-semibold text-gray-800 truncate">{user?.full_name}</p>
          <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium ${roleColors[user?.role] || 'bg-gray-100 text-gray-600'}`}>
            {roleLabels[user?.role] || user?.role}
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                }`}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Language + Logout */}
        <div className="p-3 border-t border-gray-100 space-y-1">
          <button
            onClick={toggleLang}
            className="flex items-center gap-3 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-xl w-full transition-colors"
          >
            <Languages size={18} />
            <span>{lang === 'ar' ? 'English' : 'عربي'}</span>
          </button>
          <button
            onClick={logout}
            className="flex items-center gap-3 px-4 py-2.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl w-full transition-colors"
          >
            <LogOut size={18} />
            <span>{t('logout')}</span>
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-gray-50">
        <Outlet />
      </main>
    </div>
  )
}
