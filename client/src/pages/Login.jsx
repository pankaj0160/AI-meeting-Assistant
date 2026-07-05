// client/src/pages/Login.jsx

import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, AlertCircle } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import { apiLogin } from '../api/client'
import Logo from '../components/Logo'

export default function Login() {
  const { T, isDark, toggle } = useTheme()
  const { login }    = useAuth()
  const navigate     = useNavigate()
  const location     = useLocation()
  const from         = location.state?.from?.pathname || '/app'

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await apiLogin(email, password)
      login(res.access_token, res.user)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = (focused) => ({
    width: '100%',
    padding: '12px 16px',
    borderRadius: '10px',
    border: `1px solid ${focused ? T.borderFocus : T.inputBorder}`,
    background: T.inputBg,
    color: T.text,
    fontSize: '15px',
    outline: 'none',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
    boxShadow: focused ? `0 0 0 3px ${T.accentBg}` : 'none',
    fontFamily: 'var(--font)',
  })

  return (
    <div style={{
      minHeight: '100vh',
      background: T.bg,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      transition: 'background 0.18s ease',
    }}>

      {/* Theme toggle */}
      <button
        onClick={toggle}
        style={{
          position: 'fixed', top: '20px', right: '20px',
          width: '36px', height: '36px',
          borderRadius: '9px',
          background: T.surface,
          border: `1px solid ${T.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: T.text3,
          transition: 'all 0.15s ease',
        }}
      >
        {isDark ? '☀️' : '🌙'}
      </button>

      <div className="anim-fade-up" style={{
        width: '100%', maxWidth: '420px',
      }}>

        {/* Logo — was a mic icon, now the same waveform mark used app-wide */}
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'center', marginBottom: '36px',
        }}>
          <Logo size={40} wordmarkSize={22} />
        </div>

        {/* Card */}
        <div style={{
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: '20px',
          padding: '36px',
          boxShadow: T.cardShadow,
        }}>
          <h1 style={{
            fontSize: '24px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            margin: '0 0 6px',
          }}>
            Welcome back
          </h1>
          <p style={{
            fontSize: '14px', color: T.text3,
            margin: '0 0 28px',
          }}>
            Sign in to your Summly account
          </p>

          {/* Error */}
          {error && (
            <div className="anim-fade-up" style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 16px', borderRadius: '10px',
              background: T.dangerBg,
              border: `1px solid ${T.danger}44`,
              marginBottom: '20px',
            }}>
              <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: T.danger }}>
                {error}
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit} autoComplete="off">

            {/* Email */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block', fontSize: '13px',
                fontWeight: 600, color: T.text2,
                marginBottom: '7px',
              }}>
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                style={inputStyle(false)}
                onFocus={e => Object.assign(e.target.style, {
                  borderColor: T.borderFocus,
                  boxShadow: `0 0 0 3px ${T.accentBg}`,
                })}
                onBlur={e => Object.assign(e.target.style, {
                  borderColor: T.inputBorder,
                  boxShadow: 'none',
                })}
              />
            </div>

            {/* Password */}
            <div style={{ marginBottom: '10px' }}>
              <label style={{
                display: 'block', fontSize: '13px',
                fontWeight: 600, color: T.text2,
                marginBottom: '7px',
              }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  style={{ ...inputStyle(false), paddingRight: '44px' }}
                  onFocus={e => Object.assign(e.target.style, {
                    borderColor: T.borderFocus,
                    boxShadow: `0 0 0 3px ${T.accentBg}`,
                  })}
                  onBlur={e => Object.assign(e.target.style, {
                    borderColor: T.inputBorder,
                    boxShadow: 'none',
                  })}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(s => !s)}
                  style={{
                    position: 'absolute', right: '12px',
                    top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none',
                    cursor: 'pointer', color: T.text3,
                    display: 'flex', alignItems: 'center',
                    padding: '4px',
                  }}
                >
                  {showPw
                    ? <EyeOff size={16} />
                    : <Eye size={16} />
                  }
                </button>
              </div>
            </div>

            {/* Forgot password */}
            <div style={{ textAlign: 'right', marginBottom: '24px' }}>
              <Link to="/forgot-password" style={{
                fontSize: '13px', fontWeight: 600,
                color: T.accent,
                transition: 'opacity 0.15s ease',
              }}>
                Forgot password?
              </Link>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !email || !password}
              style={{
                width: '100%',
                padding: '13px',
                borderRadius: '11px',
                background: loading || !email || !password
                  ? T.surface2 : T.btnGrad,
                border: 'none',
                color: loading || !email || !password
                  ? T.text4 : '#fff',
                fontSize: '15px',
                fontWeight: 700,
                cursor: loading || !email || !password
                  ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: loading || !email || !password
                  ? 'none' : T.btnShadow,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontFamily: 'var(--font)',
              }}
            >
              {loading
                ? <><span className="spinner" style={{
                    width: '16px', height: '16px',
                    borderColor: T.text3,
                    borderTopColor: 'transparent',
                  }} /> Signing in...</>
                : <> Sign In <ArrowRight size={16} /></>
              }
            </button>
          </form>
        </div>

        {/* Register link */}
        <p style={{
          textAlign: 'center', marginTop: '20px',
          fontSize: '14px', color: T.text3,
        }}>
          Don't have an account?{' '}
          <Link to="/register" style={{
            color: T.accent, fontWeight: 700,
            transition: 'opacity 0.15s ease',
          }}>
            Create one free
          </Link>
        </p>

      </div>
    </div>
  )
}