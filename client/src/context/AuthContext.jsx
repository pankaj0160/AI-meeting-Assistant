// client/src/context/AuthContext.jsx

import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiGetMe, setToken, removeToken, getToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,    setUser]    = useState(null)
  const [loading, setLoading] = useState(true) // true while checking token on load

  // ── On mount — restore session from localStorage ───────────────────────────
    useEffect(() => {
        const token = getToken()
        if (!token) {
        setLoading(false)
        return
        }
        apiGetMe()
        .then(u => setUser(u))
        .catch(() => {
            // Token invalid or expired — clear silently
            // ProtectedRoute will redirect to /login automatically
            removeToken()
        })
        .finally(() => setLoading(false))
    }, [])

  // ── Login — store token + set user ────────────────────────────────────────
  const login = useCallback((token, userData) => {
    setToken(token)
    setUser(userData)
  }, [])

  // ── Logout — clear everything ─────────────────────────────────────────────
  const logout = useCallback(() => {
    removeToken()
    setUser(null)
  }, [])

  // ── Update user in context after profile edit ─────────────────────────────
  const updateUser = useCallback((userData) => {
    setUser(userData)
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      isAuthenticated: !!user,
      login,
      logout,
      updateUser,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)