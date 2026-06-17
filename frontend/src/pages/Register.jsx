import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ChefHat, Building2, User, Lock, Mail, Globe, CheckCircle, Eye, EyeOff } from 'lucide-react'
import axios from 'axios'
import { useAuth } from '../context/AuthContext'

const benefits = [
  'تجربة مجانية 14 يوم بدون بطاقة',
  'إدارة الطلبات والمطبخ بالوقت الفعلي',
  'فوترة ذكية مع Stripe',
  'تقارير وإحصائيات متكاملة',
  'دعم متعدد الأجهزة وPWA',
]

export default function Register() {
  const navigate    = useNavigate()
  const { setUser } = useAuth()

  const [form, setForm] = useState({
    restaurant_name: '',
    subdomain: '',
    admin_full_name: '',
    admin_email: '',
    admin_username: '',
    admin_password: '',
  })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [step, setStep]         = useState(1)

  const update = (k, v) => {
    setForm(f => ({ ...f, [k]: v }))
    if (k === 'restaurant_name' && step === 1) {
      const slug = v.toLowerCase().replace(/[^a-z0-9]/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '')
      setForm(f => ({ ...f, restaurant_name: v, subdomain: slug }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await axios.post('/api/v1/tenants/register', form)
      const { access_token } = res.data
      localStorage.setItem('token', access_token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      const me = await axios.get('/api/v1/auth/me')
      setUser(me.data)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'حدث خطأ — حاول مرة أخرى')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen flex" dir="rtl">
      {/* Left Panel — Benefits */}
      <div className="hidden lg:flex lg:w-5/12 bg-gradient-to-br from-blue-700 to-blue-900 p-12 flex-col justify-between">
        <div>
          <div className="flex items-center gap-3 mb-12">
            <div className="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center">
              <ChefHat className="text-white" size={24} />
            </div>
            <div>
              <h1 className="text-white font-bold text-xl">نظام إدارة المطاعم</h1>
              <p className="text-blue-200 text-sm">Restaurant Management SaaS</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white mb-4 leading-relaxed">
            أدر مطعمك<br />باحترافية كاملة
          </h2>
          <p className="text-blue-200 mb-10 leading-relaxed">
            منصة SaaS متكاملة لإدارة الطلبات، المطبخ، الفوترة والمخزون. ابدأ تجربتك المجانية الآن.
          </p>

          <div className="space-y-4">
            {benefits.map((b, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-green-400 flex items-center justify-center flex-shrink-0">
                  <CheckCircle size={14} className="text-white" />
                </div>
                <span className="text-white text-sm">{b}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white/10 rounded-2xl p-5 border border-white/20">
          <p className="text-white font-bold mb-1">💡 لا تحتاج بطاقة بنكية</p>
          <p className="text-blue-200 text-sm">سجّل مجاناً وجرّب جميع الميزات لمدة 14 يوماً، ثم اختر الخطة المناسبة لك.</p>
        </div>
      </div>

      {/* Right Panel — Form */}
      <div className="flex-1 flex items-center justify-center bg-gray-50 p-6">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-3xl shadow-xl p-8">
            {/* Mobile Logo */}
            <div className="flex items-center gap-2 mb-6 lg:hidden">
              <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
                <ChefHat className="text-white" size={18} />
              </div>
              <span className="font-bold text-gray-800">نظام المطاعم</span>
            </div>

            <h2 className="text-2xl font-bold text-gray-800 mb-1">أنشئ حسابك مجاناً</h2>
            <p className="text-gray-400 text-sm mb-6">تجربة مجانية 14 يوم — لا حاجة لبطاقة بنكية</p>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl p-3 text-sm mb-5">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Restaurant Name */}
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1.5 block">اسم المطعم</label>
                <div className="relative">
                  <Building2 size={16} className="absolute right-3 top-3 text-gray-400" />
                  <input
                    value={form.restaurant_name}
                    onChange={e => update('restaurant_name', e.target.value)}
                    required placeholder="مطعم الوليمة"
                    className="w-full pr-9 pl-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Subdomain */}
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1.5 block">رابط المطعم</label>
                <div className="flex items-center border border-gray-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-blue-500">
                  <div className="relative flex-1">
                    <Globe size={16} className="absolute right-3 top-3 text-gray-400" />
                    <input
                      value={form.subdomain}
                      onChange={e => update('subdomain', e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                      required placeholder="al-walima"
                      className="w-full pr-9 pl-3 py-2.5 text-sm focus:outline-none bg-transparent"
                    />
                  </div>
                  <span className="bg-gray-50 px-3 py-2.5 text-xs text-gray-400 border-r border-gray-200 whitespace-nowrap">.restaurant.app</span>
                </div>
              </div>

              {/* Full Name + Email */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-gray-600 mb-1.5 block">اسمك</label>
                  <input
                    value={form.admin_full_name}
                    onChange={e => update('admin_full_name', e.target.value)}
                    required placeholder="أحمد محمد"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-gray-600 mb-1.5 block">البريد الإلكتروني</label>
                  <input
                    type="email"
                    value={form.admin_email}
                    onChange={e => update('admin_email', e.target.value)}
                    required placeholder="ahmed@example.com"
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Username */}
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1.5 block">اسم المستخدم</label>
                <div className="relative">
                  <User size={16} className="absolute right-3 top-3 text-gray-400" />
                  <input
                    value={form.admin_username}
                    onChange={e => update('admin_username', e.target.value)}
                    required placeholder="admin"
                    className="w-full pr-9 pl-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <label className="text-xs font-semibold text-gray-600 mb-1.5 block">كلمة المرور</label>
                <div className="relative">
                  <Lock size={16} className="absolute right-3 top-3 text-gray-400" />
                  <input
                    type={showPass ? 'text' : 'password'}
                    value={form.admin_password}
                    onChange={e => update('admin_password', e.target.value)}
                    required minLength={8} placeholder="8 أحرف على الأقل"
                    className="w-full pr-9 pl-10 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button type="button" onClick={() => setShowPass(!showPass)}
                    className="absolute left-3 top-3 text-gray-400 hover:text-gray-600">
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl transition-colors disabled:opacity-50 mt-2 text-base"
              >
                {loading ? '⏳ جاري الإنشاء...' : '🚀 أنشئ حسابي مجاناً'}
              </button>
            </form>

            <p className="text-center text-sm text-gray-400 mt-5">
              لديك حساب؟{' '}
              <Link to="/login" className="text-blue-600 font-semibold hover:underline">سجّل دخولك</Link>
            </p>
          </div>

          {/* Trial badge */}
          <div className="flex items-center justify-center gap-4 mt-6">
            {['✅ 14 يوم مجاني', '🔒 آمن 100%', '❌ لا بطاقة بنكية'].map(t => (
              <span key={t} className="text-xs text-gray-500">{t}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
