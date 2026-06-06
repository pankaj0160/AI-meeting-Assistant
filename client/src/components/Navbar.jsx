// client/src/components/Navbar.jsx

import { Link, useNavigate } from 'react-router-dom'
import { Mic, Menu, X } from 'lucide-react'
import { useState } from 'react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { T, isDark, toggle } = useTheme()
  const { isAuthenticated }   = useAuth()
  const navigate              = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const links = [
    { label: 'Features', href: '/#features' },
    { label: 'Demo',     href: '/demo'      },
    { label: 'Creator',  href: '/creator'   },
    { label: 'Support',  href: '/support'   },
  ]

  return (
    <nav style={{
        position: 'fixed',
        top: '6px',
        left: '50%',
        transform: 'translateX(-50%)',

        width: 'calc(100% - 40px)',
        maxWidth: '1320px',

        zIndex: 200,

        background: isDark
            ? 'rgba(13,17,23,0.72)'
            : 'rgba(255,255,255,0.82)',

        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',

        border: `1px solid ${T.border}`,
        borderRadius: '20px',

        boxShadow:
            '0 10px 40px rgba(0,0,0,0.08)',
        }}>
      <div style={{
        maxWidth: '1280px', margin: '0 auto',
        padding: '0 30px',
        height: '64px',
        display: 'grid',
        gridTemplateColumns: '220px 1fr auto',
        alignItems: 'center',
        gap: '40px',
      }}>

        {/* Logo */}
        <Link to="/" style={{
          display: 'flex', alignItems: 'center',
          gap: '10px', textDecoration: 'none',
        }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '12px',
            background: T.btnGrad, boxShadow: T.btnShadow,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Mic size={17} color="#fff" strokeWidth={2.5} />
          </div>
          <span style={{
            fontSize: '24px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
          }}>
            Summly
          </span>
        </Link>

        {/* Desktop nav */}
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '32px',
            fontSize: '14px',
            fontWeight: 500,
        }} className="hide-mobile">

          {links.map((l) => (
            <a
                key={l.label}
                href={l.href}
                onClick={
                l.href.startsWith('/') && !l.href.startsWith('/#')
                    ? (e) => {
                        e.preventDefault()
                        navigate(l.href)
                    }
                    : undefined
                }
                style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '28px',
                textDecoration: 'none',
                color: T.text2,
                fontSize: '14px',
                fontWeight: 500,
                transition: 'all 0.15s ease',
                cursor: 'pointer',
                }}
                onMouseEnter={(e) => {
                e.currentTarget.style.color = T.accent
                }}
                onMouseLeave={(e) => {
                e.currentTarget.style.color = T.text2
                }}
            >
                {l.icon && (
                <span
                    style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    }}
                >
                    {l.icon}
                </span>
                )}

                <span>{l.label}</span>
            </a>
            ))}

          {/* Theme toggle */}
          <button
            onClick={toggle}
            style={{
              width: '40px', height: '40px', borderRadius: '12px',
              background: T.surface2, border: `1px solid ${T.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: T.text3, marginLeft: '4px',
              transition: 'all 0.15s ease',
            }}
          >
            {isDark ? '☀️' : '🌙'}
          </button>

          {isAuthenticated ? (
            <button
              onClick={() => navigate('/app')}
              style={{
                padding: '8px 18px', borderRadius: '9px',
                background: T.btnGrad, border: 'none',
                color: '#fff', fontSize: '14px', fontWeight: 650,
                cursor: 'pointer', boxShadow: T.btnShadow,
                marginLeft: '8px', transition: 'all 0.15s ease',
                fontFamily: 'var(--font)',
              }}
            >
              Go to App →
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '8px', marginLeft: '8px', height:'60px' }}>
              <button
                onClick={() => navigate('/login')}
                style={{
                    padding: '10px 18px',
                    borderRadius: '12px',
                    background: T.surface,
                    border: `1px solid ${T.border}`,
                    color: T.text,
                    fontSize: '14px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all .25s ease',
                    fontFamily: 'var(--font)',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = T.accent
                    e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = T.border
                    e.currentTarget.style.transform = 'translateY(0)'
                }}
                >
                Sign In
                </button>
              <button
                onClick={() => navigate('/register')}
                style={{
                    padding: '10px 22px',
                    borderRadius: '14px',

                    background:
                    'linear-gradient(135deg, #7c3aed 0%, #6366f1 50%, #0ea5e9 100%)',

                    border: 'none',

                    color: '#fff',
                    fontSize: '14px',
                    fontWeight: 700,

                    cursor: 'pointer',

                    letterSpacing: '-0.02em',

                    boxShadow:
                    '0 10px 25px rgba(99,102,241,.35), 0 2px 8px rgba(0,0,0,.08)',

                    transition: 'all .25s ease',

                    fontFamily: 'var(--font)',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow =
                    '0 14px 35px rgba(99,102,241,.45)'
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow =
                    '0 10px 25px rgba(99,102,241,.35), 0 2px 8px rgba(0,0,0,.08)'
                }}
                >
                Get Started Free
                </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}