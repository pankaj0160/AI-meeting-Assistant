// client/src/pages/Register.jsx

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import { apiRegister } from '../api/client'
import Logo from '../components/Logo'

export default function Register() {
  const { T, isDark, toggle } = useTheme()
  const { login }  = useAuth()
  const navigate   = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)

  // Password strength
  const pwStrength = (() => {
    if (password.length === 0) return null
    if (password.length < 8)  return { level: 0, label: 'Too short',  color: '#ef4444' }
    if (password.length < 12) return { level: 1, label: 'Weak',       color: '#f59e0b' }
    if (/[A-Z]/.test(password) && /[0-9]/.test(password))
                               return { level: 3, label: 'Strong',     color: '#10b981' }
    return                            { level: 2, label: 'Good',       color: '#3b82f6' }
  })()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const res = await apiRegister(fullName, email, password)
      login(res.access_token, res.user)
      navigate('/app', { replace: true })
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '12px 16px',
    borderRadius: '10px',
    border: `1px solid ${T.inputBorder}`,
    background: T.inputBg, color: T.text,
    fontSize: '15px', outline: 'none',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
    fontFamily: 'var(--font)',
  }

  const focusStyle = {
    borderColor: T.borderFocus,
    boxShadow: `0 0 0 3px ${T.accentBg}`,
  }

  const blurStyle = {
    borderColor: T.inputBorder,
    boxShadow: 'none',
  }

  return (
    <div style={{
      minHeight: '100vh', background: T.bg,
      display: 'flex', alignItems: 'center',
      justifyContent: 'center', padding: '24px',
      transition: 'background 0.18s ease',
    }}>

      <button
        onClick={toggle}
        style={{
          position: 'fixed', top: '20px', right: '20px',
          width: '36px', height: '36px', borderRadius: '9px',
          background: T.surface, border: `1px solid ${T.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', color: T.text3,
        }}
      >
        {isDark ? '☀️' : '🌙'}
      </button>

      <div className="anim-fade-up" style={{ width: '100%', maxWidth: '440px' }}>

        {/* Logo — was a mic icon, now the same waveform mark used app-wide */}
        <div style={{
          display: 'flex', alignItems: 'center',
          justifyContent: 'center', marginBottom: '36px',
        }}>
          <Logo size={40} wordmarkSize={22} />
        </div>

        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: '20px', padding: '36px',
          boxShadow: T.cardShadow,
        }}>
          <h1 style={{
            fontSize: '24px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            margin: '0 0 6px',
          }}>
            Create your account
          </h1>
          <p style={{
            fontSize: '14px', color: T.text3,
            margin: '0 0 28px',
          }}>
            Free forever. No credit card required.
          </p>

          {error && (
            <div className="anim-fade-up" style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 16px', borderRadius: '10px',
              background: T.dangerBg,
              border: `1px solid ${T.danger}44`,
              marginBottom: '20px',
            }}>
              <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: T.danger }}>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} autoComplete="off">

            {/* Full name */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block', fontSize: '13px',
                fontWeight: 600, color: T.text2, marginBottom: '7px',
              }}>
                Full name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={e => setFullName(e.target.value)}
                placeholder="Pankaj Thakur"
                required
                style={inputStyle}
                onFocus={e => Object.assign(e.target.style, focusStyle)}
                onBlur={e => Object.assign(e.target.style, blurStyle)}
              />
            </div>

            {/* Email */}
            <div style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'block', fontSize: '13px',
                fontWeight: 600, color: T.text2, marginBottom: '7px',
              }}>
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                style={inputStyle}
                onFocus={e => Object.assign(e.target.style, focusStyle)}
                onBlur={e => Object.assign(e.target.style, blurStyle)}
              />
            </div>

            {/* Password */}
            <div style={{ marginBottom: '8px' }}>
              <label style={{
                display: 'block', fontSize: '13px',
                fontWeight: 600, color: T.text2, marginBottom: '7px',
              }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  required
                  minLength={8}
                  style={{ ...inputStyle, paddingRight: '44px' }}
                  onFocus={e => Object.assign(e.target.style, focusStyle)}
                  onBlur={e => Object.assign(e.target.style, blurStyle)}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(s => !s)}
                  style={{
                    position: 'absolute', right: '12px',
                    top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none',
                    cursor: 'pointer', color: T.text3,
                    display: 'flex', alignItems: 'center', padding: '4px',
                  }}
                >
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Password strength indicator */}
            {pwStrength && (
              <div style={{ marginBottom: '20px' }}>
                <div style={{
                  display: 'flex', gap: '4px', marginBottom: '5px',
                }}>
                  {[0, 1, 2, 3].map(i => (
                    <div key={i} style={{
                      flex: 1, height: '3px', borderRadius: '99px',
                      background: i <= pwStrength.level
                        ? pwStrength.color
                        : T.border,
                      transition: 'background 0.2s ease',
                    }} />
                  ))}
                </div>
                <div style={{
                  fontSize: '12px', fontWeight: 600,
                  color: pwStrength.color,
                }}>
                  {pwStrength.label}
                </div>
              </div>
            )}

            {/* Benefits */}
            <div style={{
              padding: '14px 16px',
              borderRadius: '10px',
              background: T.emeraldBg,
              border: `1px solid ${T.emerald}22`,
              marginBottom: '24px',
            }}>
              {[
                'Unlimited uploads',
                'Full AI intelligence',
                'Cross-meeting search',
                'Everything free forever',
              ].map(item => (
                <div key={item} style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  fontSize: '12.5px', color: T.emeraldText,
                  fontWeight: 500, marginBottom: '4px',
                }}>
                  <CheckCircle size={12} color={T.emerald} />
                  {item}
                </div>
              ))}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !fullName || !email || password.length < 8}
              style={{
                width: '100%', padding: '13px',
                borderRadius: '11px',
                background: loading || !fullName || !email || password.length < 8
                  ? T.surface2 : T.btnGrad,
                border: 'none',
                color: loading || !fullName || !email || password.length < 8
                  ? T.text4 : '#fff',
                fontSize: '15px', fontWeight: 700,
                cursor: loading || !fullName || !email || password.length < 8
                  ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
                boxShadow: loading || !fullName || !email || password.length < 8
                  ? 'none' : T.btnShadow,
                display: 'flex', alignItems: 'center',
                justifyContent: 'center', gap: '8px',
                fontFamily: 'var(--font)',
              }}
            >
              {loading
                ? <><span className="spinner" style={{
                    width: '16px', height: '16px',
                    borderColor: T.text3,
                    borderTopColor: 'transparent',
                  }} /> Creating account...</>
                : <>Create Free Account <ArrowRight size={16} /></>
              }
            </button>
          </form>
        </div>

        <p style={{
          textAlign: 'center', marginTop: '20px',
          fontSize: '14px', color: T.text3,
        }}>
          Already have an account?{' '}
          <Link to="/login" style={{
            color: T.accent, fontWeight: 700,
          }}>
            Sign in
          </Link>
        </p>

      </div>
    </div>
  )
}