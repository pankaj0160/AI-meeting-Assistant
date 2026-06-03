// client/src/components/ProtectedRoute.jsx

import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../ThemeContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const { T } = useTheme()
  const location = useLocation()

  // Show spinner while checking token
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: T.bg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: '16px',
      }}>
        <div style={{
          width: '40px', height: '40px',
          borderRadius: '12px',
          background: T.btnGrad,
          display: 'flex', alignItems: 'center',
          justifyContent: 'center',
          boxShadow: T.btnShadow,
        }}>
          <span style={{ fontSize: '20px' }}>🎙</span>
        </div>
        <div className="spinner" style={{
          borderColor: T.accent,
          borderTopColor: 'transparent',
          width: '22px', height: '22px',
        }} />
      </div>
    )
  }

  if (!isAuthenticated) {
    // Save attempted location so we can redirect after login
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}