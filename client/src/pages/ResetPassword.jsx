// client/src/pages/ResetPassword.jsx
//
// PHASE 1 FIX: this page did not exist. The backend's forgot-password
// flow now emails a real link to /reset-password?token=... (see
// core/email.py + core/auth/router.py), but there was nowhere for that
// link to actually go — it would have 404'd. This page reads the token
// from the URL and lets the user set a new password.

import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, AlertCircle, CheckCircle, ArrowLeft, Lock } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { apiResetPassword } from '../api/client'
import Logo from '../components/Logo'

export default function ResetPassword() {
  const { T } = useTheme()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password,        setPassword]        = useState('')
  const [confirmPassword, setConfirmPassword]  = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.")
      return
    }

    setLoading(true)
    try {
      await apiResetPassword(token, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2500)
    } catch (err) {
      // Backend returns a generic error for expired/invalid tokens —
      // never confirm/deny which case it was, same enumeration-safety
      // principle as the forgot-password endpoint itself.
      setError(err.message || 'This reset link is invalid or has expired.')
    } finally {
      setLoading(false)
    }
  }

  // No token in the URL at all — someone navigated here directly rather
  // than clicking the emailed link. Send them to request one instead of
  // showing a broken form.
  if (!token) {
    return (
      <div style={{
        minHeight: '100vh', background: T.bg,
        display: 'flex', alignItems: 'center',
        justifyContent: 'center', padding: '24px',
      }}>
        <div className="anim-fade-up" style={{ width: '100%', maxWidth: '400px', textAlign: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '36px' }}>
            <Logo size={40} wordmarkSize={22} />
          </div>
          <div style={{
            background: T.surface, border: `1px solid ${T.border}`,
            borderRadius: '20px', padding: '36px',
            boxShadow: T.cardShadow,
          }}>
            <AlertCircle size={32} color={T.danger} style={{ marginBottom: '14px' }} />
            <div style={{ fontSize: '15px', fontWeight: 600, color: T.text, marginBottom: '8px' }}>
              Missing reset link
            </div>
            <div style={{ fontSize: '13px', color: T.text3, lineHeight: 1.6, marginBottom: '20px' }}>
              This page needs a valid reset link from your email. Request a new one below.
            </div>
            <Link to="/forgot-password" style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              padding: '11px 20px', borderRadius: '10px',
              background: T.btnGrad, color: '#fff',
              fontSize: '14px', fontWeight: 700, textDecoration: 'none',
            }}>
              Request reset link <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh', background: T.bg,
      display: 'flex', alignItems: 'center',
      justifyContent: 'center', padding: '24px',
    }}>
      <div className="anim-fade-up" style={{ width: '100%', maxWidth: '400px' }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '36px' }}>
          <Logo size={40} wordmarkSize={22} />
        </div>

        <div style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: '20px', padding: '36px',
          boxShadow: T.cardShadow,
        }}>
          <h1 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.04em', color: T.text, margin: '0 0 6px' }}>
            Set a new password
          </h1>
          <p style={{ fontSize: '14px', color: T.text3, margin: '0 0 24px', lineHeight: 1.5 }}>
            Choose a new password for your account.
          </p>

          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 16px', borderRadius: '10px',
              background: T.dangerBg, border: `1px solid ${T.danger}44`,
              marginBottom: '18px',
            }}>
              <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: T.danger }}>{error}</span>
            </div>
          )}

          {success ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '16px 0' }}>
              <CheckCircle size={40} color={T.accent} style={{ marginBottom: '14px' }} />
              <div style={{ fontSize: '15px', fontWeight: 600, color: T.text, marginBottom: '8px' }}>
                Password updated
              </div>
              <div style={{ fontSize: '13px', color: T.text3, lineHeight: 1.6 }}>
                Redirecting you to sign in...
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} autoComplete="off">
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: T.text2, marginBottom: '7px' }}>
                  New password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={15} color={T.text3} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                    minLength={8}
                    style={{
                      width: '100%', padding: '12px 16px 12px 40px',
                      borderRadius: '10px', border: `1px solid ${T.inputBorder}`,
                      background: T.inputBg, color: T.text,
                      fontSize: '15px', outline: 'none', fontFamily: 'var(--font)',
                      boxSizing: 'border-box',
                    }}
                    onFocus={e => { e.target.style.borderColor = T.borderFocus; e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}` }}
                    onBlur={e => { e.target.style.borderColor = T.inputBorder; e.target.style.boxShadow = 'none' }}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: T.text2, marginBottom: '7px' }}>
                  Confirm new password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={15} color={T.text3} style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your new password"
                    required
                    minLength={8}
                    style={{
                      width: '100%', padding: '12px 16px 12px 40px',
                      borderRadius: '10px', border: `1px solid ${T.inputBorder}`,
                      background: T.inputBg, color: T.text,
                      fontSize: '15px', outline: 'none', fontFamily: 'var(--font)',
                      boxSizing: 'border-box',
                    }}
                    onFocus={e => { e.target.style.borderColor = T.borderFocus; e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}` }}
                    onBlur={e => { e.target.style.borderColor = T.inputBorder; e.target.style.boxShadow = 'none' }}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !password || !confirmPassword}
                style={{
                  width: '100%', padding: '13px', borderRadius: '11px',
                  background: loading || !password || !confirmPassword ? T.surface2 : T.btnGrad,
                  border: 'none',
                  color: loading || !password || !confirmPassword ? T.text4 : '#fff',
                  fontSize: '15px', fontWeight: 700,
                  cursor: loading || !password || !confirmPassword ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  fontFamily: 'var(--font)',
                  boxShadow: loading || !password || !confirmPassword ? 'none' : T.btnShadow,
                }}
              >
                {loading
                  ? <><span className="spinner" style={{ width: '16px', height: '16px', borderColor: T.text3, borderTopColor: 'transparent' }} /> Updating...</>
                  : <>Update Password <ArrowRight size={16} /></>
                }
              </button>
            </form>
          )}
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Link to="/login" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '14px', fontWeight: 600, color: T.text3 }}>
            <ArrowLeft size={14} /> Back to Sign In
          </Link>
        </div>

      </div>
    </div>
  )
}