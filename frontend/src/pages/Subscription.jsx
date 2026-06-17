import { useState, useEffect } from 'react'
import { CheckCircle, Zap, Crown, Building2, RefreshCw, ExternalLink, AlertCircle, Clock } from 'lucide-react'
import axios from 'axios'

const PLANS = [
  {
    key: 'Free',
    name: 'مجاني',
    nameEn: 'Free',
    price: 0,
    period: '',
    color: 'border-gray-200',
    badge: '',
    icon: '🆓',
    description: 'للتجربة والمطاعم الصغيرة',
    features: [
      '3 مستخدمين',
      '5 طاولات',
      'إدارة طلبات أساسية',
      'قائمة الطعام',
      'تجربة 14 يوم مجاناً',
    ],
    disabled: true,
  },
  {
    key: 'Basic',
    name: 'أساسي',
    nameEn: 'Basic',
    price: 99,
    period: '/شهر',
    color: 'border-blue-300',
    badge: 'الأكثر شيوعاً',
    icon: '⚡',
    description: 'للمطاعم المتوسطة',
    features: [
      '10 مستخدمين',
      '20 طاولة',
      'كل ميزات المجاني +',
      'شاشة المطبخ الفورية',
      'تقارير مبيعات',
      'فوترة PDF',
      'دعم فني',
    ],
  },
  {
    key: 'Pro',
    name: 'احترافي',
    nameEn: 'Pro',
    price: 299,
    period: '/شهر',
    color: 'border-purple-400',
    badge: '🔥 الأفضل قيمة',
    icon: '👑',
    description: 'للمطاعم الكبيرة والسلاسل',
    features: [
      '50 مستخدماً',
      '100 طاولة',
      'كل ميزات الأساسي +',
      'دعم Stripe كامل',
      'تكامل واتساب',
      'تحليلات متقدمة',
      'أولوية الدعم الفني',
    ],
  },
  {
    key: 'Enterprise',
    name: 'مؤسسي',
    nameEn: 'Enterprise',
    price: null,
    period: '',
    color: 'border-yellow-400',
    badge: '',
    icon: '🏢',
    description: 'للسلاسل والمجموعات',
    features: [
      'مستخدمون غير محدودين',
      'طاولات غير محدودة',
      'كل ميزات الاحترافي +',
      'API مخصص',
      'White-label',
      'مدير حساب مخصص',
      'SLA مضمون',
    ],
    custom: true,
  },
]

const statusConfig = {
  Trialing:  { label: 'تجربة مجانية', color: 'bg-blue-50 text-blue-700 border-blue-200', icon: Clock },
  Active:    { label: 'نشط',          color: 'bg-green-50 text-green-700 border-green-200', icon: CheckCircle },
  PastDue:   { label: 'دفعة متأخرة', color: 'bg-red-50 text-red-600 border-red-200',   icon: AlertCircle },
  Cancelled: { label: 'ملغي',         color: 'bg-gray-100 text-gray-500 border-gray-200', icon: AlertCircle },
  Expired:   { label: 'منتهي',        color: 'bg-red-50 text-red-600 border-red-200',   icon: AlertCircle },
}

export default function Subscription() {
  const [subStatus, setSubStatus] = useState(null)
  const [loading, setLoading]     = useState(true)
  const [upgrading, setUpgrading] = useState('')
  const [portalLoading, setPortalLoading] = useState(false)

  const fetchStatus = async () => {
    setLoading(true)
    try {
      const res = await axios.get('/api/v1/tenants/billing/status')
      setSubStatus(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { fetchStatus() }, [])

  const upgrade = async (planKey) => {
    setUpgrading(planKey)
    try {
      const res = await axios.post('/api/v1/tenants/billing/subscribe', { plan: planKey })
      window.location.href = res.data.checkout_url
    } catch (err) {
      alert(err.response?.data?.detail || 'حدث خطأ — تأكد من إعداد Stripe')
    }
    setUpgrading('')
  }

  const openPortal = async () => {
    setPortalLoading(true)
    try {
      const res = await axios.post('/api/v1/tenants/billing/portal')
      window.location.href = res.data.portal_url
    } catch (err) {
      alert(err.response?.data?.detail || 'حدث خطأ')
    }
    setPortalLoading(false)
  }

  const currentPlan = subStatus?.plan || 'Free'
  const StatusIcon = statusConfig[subStatus?.status]?.icon || CheckCircle

  return (
    <div className="p-6" dir="rtl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">الاشتراك والخطط</h1>
          <p className="text-sm text-gray-400 mt-1">إدارة خطة اشتراكك وتفاصيل الفوترة</p>
        </div>
        <button onClick={fetchStatus} className="flex items-center gap-2 text-sm text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-xl border border-blue-200">
          <RefreshCw size={15} /> تحديث
        </button>
      </div>

      {/* Current Plan Card */}
      {!loading && subStatus && (
        <div className="bg-gradient-to-l from-blue-600 to-blue-700 rounded-2xl p-6 mb-8 text-white">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-blue-200 text-sm mb-1">خطتك الحالية</p>
              <h2 className="text-3xl font-black">{PLANS.find(p => p.key === currentPlan)?.name || currentPlan}</h2>
              <div className="flex items-center gap-3 mt-3">
                <span className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-full font-semibold border ${statusConfig[subStatus.status]?.color}`}>
                  <StatusIcon size={12} />
                  {statusConfig[subStatus.status]?.label || subStatus.status}
                </span>
                {subStatus.current_period_end && (
                  <span className="text-blue-200 text-xs">
                    ينتهي: {new Date(subStatus.current_period_end).toLocaleDateString('ar')}
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="bg-white/10 rounded-xl p-3 text-center">
                <p className="text-blue-200 text-xs">المستخدمون</p>
                <p className="text-2xl font-black">{subStatus.max_users === -1 ? '∞' : subStatus.max_users}</p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-5">
            {[
              { label: 'الطاولات', value: subStatus.max_tables === -1 ? '∞' : subStatus.max_tables },
              { label: 'المستخدمون', value: subStatus.max_users === -1 ? '∞' : subStatus.max_users },
              { label: 'الحالة', value: statusConfig[subStatus.status]?.label },
            ].map(({ label, value }) => (
              <div key={label} className="bg-white/10 rounded-xl p-3 text-center">
                <p className="text-blue-200 text-xs mb-1">{label}</p>
                <p className="font-bold">{value}</p>
              </div>
            ))}
          </div>

          {subStatus.plan !== 'Free' && (
            <button
              onClick={openPortal}
              disabled={portalLoading}
              className="mt-5 flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
            >
              <ExternalLink size={14} />
              {portalLoading ? 'جاري الفتح...' : 'إدارة الفوترة في Stripe'}
            </button>
          )}
        </div>
      )}

      {/* Plans Grid */}
      <h2 className="text-lg font-bold text-gray-800 mb-5">اختر خطتك</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        {PLANS.map(plan => {
          const isCurrent = plan.key === currentPlan
          const isPro     = plan.key === 'Pro'

          return (
            <div key={plan.key}
              className={`bg-white rounded-2xl border-2 p-5 relative transition-all ${isCurrent ? 'border-blue-500 shadow-lg shadow-blue-100' : plan.color} ${isPro ? 'ring-2 ring-purple-400 ring-offset-2' : ''}`}>

              {/* Badge */}
              {plan.badge && (
                <div className={`absolute -top-3 right-4 text-xs font-bold px-3 py-1 rounded-full ${isPro ? 'bg-purple-600 text-white' : 'bg-blue-600 text-white'}`}>
                  {plan.badge}
                </div>
              )}
              {isCurrent && (
                <div className="absolute -top-3 left-4 text-xs font-bold px-3 py-1 rounded-full bg-green-500 text-white">
                  ✅ خطتك الحالية
                </div>
              )}

              <div className="text-3xl mb-3">{plan.icon}</div>
              <h3 className="text-lg font-black text-gray-800">{plan.name}</h3>
              <p className="text-gray-400 text-xs mb-4">{plan.description}</p>

              {plan.custom ? (
                <div className="mb-4">
                  <span className="text-2xl font-black text-gray-800">تواصل معنا</span>
                </div>
              ) : (
                <div className="mb-4 flex items-end gap-1">
                  <span className="text-3xl font-black text-gray-800">{plan.price}</span>
                  <span className="text-gray-400 text-sm mb-1">ر.س{plan.period}</span>
                </div>
              )}

              <div className="space-y-2 mb-5">
                {plan.features.map((f, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                    <CheckCircle size={14} className="text-green-500 flex-shrink-0 mt-0.5" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>

              {plan.custom ? (
                <a href="mailto:sales@restaurant.app"
                  className="w-full flex items-center justify-center gap-2 bg-yellow-500 hover:bg-yellow-600 text-white py-2.5 rounded-xl font-bold text-sm transition-colors">
                  تواصل معنا
                </a>
              ) : isCurrent ? (
                <button disabled className="w-full bg-green-50 text-green-600 border border-green-200 py-2.5 rounded-xl font-bold text-sm cursor-default">
                  ✅ خطتك الحالية
                </button>
              ) : plan.disabled ? (
                <button disabled className="w-full bg-gray-50 text-gray-400 border border-gray-200 py-2.5 rounded-xl font-bold text-sm cursor-not-allowed">
                  الخطة الافتراضية
                </button>
              ) : (
                <button
                  onClick={() => upgrade(plan.key)}
                  disabled={!!upgrading}
                  className={`w-full py-2.5 rounded-xl font-bold text-sm transition-colors flex items-center justify-center gap-2 ${
                    isPro
                      ? 'bg-purple-600 hover:bg-purple-700 text-white'
                      : 'bg-blue-600 hover:bg-blue-700 text-white'
                  } disabled:opacity-50`}
                >
                  {upgrading === plan.key ? (
                    <><div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> جاري التحويل...</>
                  ) : (
                    <><Zap size={14} /> ترقية إلى {plan.name}</>
                  )}
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Info Banner */}
      <div className="mt-8 bg-blue-50 border border-blue-100 rounded-2xl p-5 flex gap-4">
        <AlertCircle className="text-blue-500 flex-shrink-0 mt-0.5" size={20} />
        <div>
          <p className="font-semibold text-blue-800 text-sm">معلومات الفوترة</p>
          <p className="text-blue-600 text-sm mt-1">
            جميع الأسعار بالريال السعودي شاملة ضريبة القيمة المضافة. يمكنك إلغاء اشتراكك في أي وقت من Stripe Portal.
            عند الترقية، يتم احتساب الرسوم بشكل تناسبي من تاريخ الترقية.
          </p>
        </div>
      </div>
    </div>
  )
}
