import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { I18nProvider } from './context/i18n'
import Login from './pages/Login'
import CustomerOrder from './pages/CustomerOrder'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Menu from './pages/Menu'
import Orders from './pages/Orders'
import Tables from './pages/Tables'
import Inventory from './pages/Inventory'
import Reports from './pages/Reports'
import Users from './pages/Users'
import Billing from './pages/Billing'
import Kitchen from './pages/Kitchen'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
    </div>
  )
  return user ? children : <Navigate to="/login" replace />
}

function App() {
  return (
    <I18nProvider>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/order/:qrToken" element={<CustomerOrder />} />
          <Route path="/login" element={<Login />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }>
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="menu" element={<Menu />} />
            <Route path="orders" element={<Orders />} />
            <Route path="tables" element={<Tables />} />
            <Route path="inventory" element={<Inventory />} />
            <Route path="reports" element={<Reports />} />
            <Route path="users" element={<Users />} />
            <Route path="billing" element={<Billing />} />
            <Route path="kitchen" element={<Kitchen />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
    </I18nProvider>
  )
}

export default App
