// client/src/pages/ForgotPassword.jsx

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, AlertCircle, CheckCircle, ArrowLeft } from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { apiForgotPassword } from '../api/client'
import Logo from '../components/Logo'

export default function ForgotPassword() {
  const { T } = useTheme()
  const [email,   setEmail]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [success, setSuccess] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await apiForgotPassword(email)
      setSuccess(res.message)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', background: T.bg,
      display: 'flex', alignItems: 'center',
      justifyContent: 'center', padding: '24px',
    }}>
      <div className="anim-fade-up" style={{ width: '100%', maxWidth: '400px' }}>

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
            fontSize: '22px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            margin: '0 0 6px',
          }}>
            Reset password
          </h1>
          <p style={{
            fontSize: '14px', color: T.text3,
            margin: '0 0 24px', lineHeight: 1.5,
          }}>
            Enter your email address and we'll send you a link to reset your password.
          </p>

          {error && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '12px 16px', borderRadius: '10px',
              background: T.dangerBg,
              border: `1px solid ${T.danger}44`,
              marginBottom: '18px',
            }}>
              <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: '13px', color: T.danger }}>{error}</span>
            </div>
          )}

          {success ? (
            <div style={{
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', textAlign: 'center',
              padding: '16px 0',
            }}>
              <CheckCircle size={40} color={T.emerald} style={{ marginBottom: '14px' }} />
              <div style={{
                fontSize: '15px', fontWeight: 600,
                color: T.text, marginBottom: '8px',
              }}>
                Check your email
              </div>
              <div style={{
                fontSize: '13px', color: T.text3,
                lineHeight: 1.6, marginBottom: '4px',
              }}>
                {success}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} autoComplete="off">
              <div style={{ marginBottom: '20px' }}>
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
                  style={{
                    width: '100%', padding: '12px 16px',
                    borderRadius: '10px',
                    border: `1px solid ${T.inputBorder}`,
                    background: T.inputBg, color: T.text,
                    fontSize: '15px', outline: 'none',
                    fontFamily: 'var(--font)',
                  }}
                  onFocus={e => {
                    e.target.style.borderColor = T.borderFocus
                    e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}`
                  }}
                  onBlur={e => {
                    e.target.style.borderColor = T.inputBorder
                    e.target.style.boxShadow = 'none'
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={loading || !email}
                style={{
                  width: '100%', padding: '13px',
                  borderRadius: '11px',
                  background: loading || !email ? T.surface2 : T.btnGrad,
                  border: 'none',
                  color: loading || !email ? T.text4 : '#fff',
                  fontSize: '15px', fontWeight: 700,
                  cursor: loading || !email ? 'not-allowed' : 'pointer',
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'center', gap: '8px',
                  fontFamily: 'var(--font)',
                  boxShadow: loading || !email ? 'none' : T.btnShadow,
                }}
              >
                {loading
                  ? <><span className="spinner" style={{
                      width: '16px', height: '16px',
                      borderColor: T.text3,
                      borderTopColor: 'transparent',
                    }} /> Sending...</>
                  : <>Send Reset Token <ArrowRight size={16} /></>
                }
              </button>
            </form>
          )}
        </div>

        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <Link to="/login" style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            fontSize: '14px', fontWeight: 600, color: T.text3,
            transition: 'color 0.15s ease',
          }}>
            <ArrowLeft size={14} /> Back to Sign In
          </Link>
        </div>

      </div>
    </div>
  )
}