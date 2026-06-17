import { createContext, useContext, useState } from 'react'

const translations = {
  ar: {
    appName: 'نظام إدارة المطاعم',
    dashboard: 'الرئيسية',
    orders: 'الطلبات',
    tables: 'الطاولات',
    menu: 'القائمة',
    inventory: 'المخزون',
    billing: 'الفوترة والدفع',
    reports: 'التقارير',
    users: 'المستخدمين',
    logout: 'تسجيل الخروج',
    addNew: 'إضافة جديد',
    save: 'حفظ',
    cancel: 'إلغاء',
    delete: 'حذف',
    edit: 'تعديل',
    refresh: 'تحديث',
    loading: 'جاري التحميل...',
    noData: 'لا توجد بيانات',
    total: 'الإجمالي',
    search: 'بحث...',
    login: 'دخول',
    username: 'اسم المستخدم',
    password: 'كلمة المرور',
    // Orders
    newOrder: 'طلب جديد',
    orderNum: 'طلب',
    table: 'طاولة',
    status: 'الحالة',
    pending: 'انتظار',
    preparing: 'تحضير',
    ready: 'جاهز',
    delivered: 'مُسلَّم',
    cancelled: 'ملغي',
    startPreparing: 'ابدأ التحضير',
    readyToDeliver: 'جاهز للتسليم',
    delivered2: 'تم التسليم',
    // Billing
    invoice: 'فاتورة',
    subtotal: 'المجموع الفرعي',
    tax: 'الضريبة',
    discount: 'خصم',
    payByCash: 'نقداً',
    payByCard: 'بطاقة',
    couponCode: 'كود الخصم',
    applyCoupon: 'تطبيق',
    paymentSuccess: 'تم الدفع بنجاح!',
    issueInvoice: 'إصدار فاتورة ودفع',
    // Reports
    revenue: 'الإيرادات',
    totalRevenue: 'إجمالي الإيرادات',
    invoiceCount: 'عدد الفواتير',
    avgOrder: 'متوسط الطلب',
    trending: 'الأكثر طلباً',
    dailyRevenue: 'الإيرادات اليومية',
    today: 'اليوم',
    thisMonth: 'هذا الشهر',
    // Menu
    addItem: 'إضافة صنف',
    price: 'السعر',
    available: 'متاح',
    unavailable: 'غير متاح',
    category: 'الفئة',
    allCategories: 'الكل',
    // Users
    addUser: 'إضافة مستخدم',
    fullName: 'الاسم الكامل',
    role: 'الدور',
    phone: 'الهاتف',
    active: 'نشط',
    inactive: 'معطل',
    roles: { Admin: 'مدير', Cashier: 'كاشير', Waiter: 'نادل', Chef: 'طاهي' },
  },
  en: {
    appName: 'Restaurant Management',
    dashboard: 'Dashboard',
    orders: 'Orders',
    tables: 'Tables',
    menu: 'Menu',
    inventory: 'Inventory',
    billing: 'Billing & Payment',
    reports: 'Reports',
    users: 'Users',
    logout: 'Logout',
    addNew: 'Add New',
    save: 'Save',
    cancel: 'Cancel',
    delete: 'Delete',
    edit: 'Edit',
    refresh: 'Refresh',
    loading: 'Loading...',
    noData: 'No data found',
    total: 'Total',
    search: 'Search...',
    login: 'Login',
    username: 'Username',
    password: 'Password',
    newOrder: 'New Order',
    orderNum: 'Order',
    table: 'Table',
    status: 'Status',
    pending: 'Pending',
    preparing: 'Preparing',
    ready: 'Ready',
    delivered: 'Delivered',
    cancelled: 'Cancelled',
    startPreparing: 'Start Preparing',
    readyToDeliver: 'Ready to Deliver',
    delivered2: 'Mark Delivered',
    invoice: 'Invoice',
    subtotal: 'Subtotal',
    tax: 'Tax',
    discount: 'Discount',
    payByCash: 'Cash',
    payByCard: 'Card',
    couponCode: 'Coupon Code',
    applyCoupon: 'Apply',
    paymentSuccess: 'Payment Successful!',
    issueInvoice: 'Issue Invoice & Pay',
    revenue: 'Revenue',
    totalRevenue: 'Total Revenue',
    invoiceCount: 'Invoices',
    avgOrder: 'Avg. Order',
    trending: 'Top Items',
    dailyRevenue: 'Daily Revenue',
    today: 'Today',
    thisMonth: 'This Month',
    addItem: 'Add Item',
    price: 'Price',
    available: 'Available',
    unavailable: 'Unavailable',
    category: 'Category',
    allCategories: 'All',
    addUser: 'Add User',
    fullName: 'Full Name',
    role: 'Role',
    phone: 'Phone',
    active: 'Active',
    inactive: 'Inactive',
    roles: { Admin: 'Admin', Cashier: 'Cashier', Waiter: 'Waiter', Chef: 'Chef' },
  },
}

const I18nContext = createContext(null)

export const useI18n = () => useContext(I18nContext)

export function I18nProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'ar')

  const toggleLang = () => {
    const next = lang === 'ar' ? 'en' : 'ar'
    setLang(next)
    localStorage.setItem('lang', next)
    document.documentElement.dir = next === 'ar' ? 'rtl' : 'ltr'
    document.documentElement.lang = next
  }

  const t = (key) => {
    const keys = key.split('.')
    let val = translations[lang]
    for (const k of keys) val = val?.[k]
    return val ?? key
  }

  return (
    <I18nContext.Provider value={{ lang, toggleLang, t, isRTL: lang === 'ar' }}>
      {children}
    </I18nContext.Provider>
  )
}
