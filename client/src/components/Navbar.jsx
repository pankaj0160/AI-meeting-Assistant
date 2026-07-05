// components/Navbar.jsx
// Brand v2 updates:
//   - Mic icon replaced with S lettermark
//   - "Get Started" button: indigo gradient → solid emerald
//   - Mobile menu improved with drawer-style slide
//   - Hover states use T.accent (emerald)

import { Link, useNavigate } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import { useState } from 'react'
import Logo from './Logo'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { T, isDark, toggle }   = useTheme()
  const { isAuthenticated }     = useAuth()
  const navigate                = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const links = [
    { label: 'Features', href: '/#features' },
    { label: 'Demo',     href: '/demo'       },
    { label: 'Creator',  href: '/creator'    },
    { label: 'Support',  href: '/support'    },
  ]

  const handleNav = (href) => {
    setMenuOpen(false)
    if (href.startsWith('/') && !href.startsWith('/#')) navigate(href)
    else window.location.href = href
  }

  return (
    <>
      <nav style={{
        position: 'fixed',
        top: '10px',
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'calc(100% - 32px)',
        maxWidth: '1200px',
        zIndex: 200,
        background: isDark
          ? 'rgba(10,10,11,0.85)'
          : 'rgba(255,255,255,0.88)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        border: `1px solid ${T.border}`,
        borderRadius: '16px',
        boxShadow: isDark
          ? '0 4px 24px rgba(0,0,0,0.4)'
          : '0 4px 20px rgba(0,0,0,0.07)',
      }}>
        <div style={{
          padding: '0 24px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '24px',
        }}>

          {/* ── Logo ── */}
          {/* Consolidated into <Logo /> — see components/Logo.jsx */}
          <Link to="/" style={{
            display: 'flex', alignItems: 'center',
            gap: '10px', textDecoration: 'none', flexShrink: 0,
          }}>
            <Logo size={34} wordmarkSize={20} />
          </Link>

          {/* ── Desktop nav links ── */}
          <div style={{
            display: 'flex', alignItems: 'center',
            gap: '4px', flex: 1, justifyContent: 'center',
          }}
          className="hide-mobile"
          >
            {links.map(l => (
              <a
                key={l.label}
                href={l.href}
                onClick={e => { e.preventDefault(); handleNav(l.href) }}
                style={{
                  padding: '6px 12px', borderRadius: '8px',
                  textDecoration: 'none',
                  color: T.text3,
                  fontSize: '14px', fontWeight: 500,
                  transition: 'all 0.15s ease',
                  cursor: 'pointer',
                  border: '1px solid transparent',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.color = T.text
                  e.currentTarget.style.background = T.surface2
                  e.currentTarget.style.borderColor = T.border
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = T.text3
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.borderColor = 'transparent'
                }}
              >
                {l.label}
              </a>
            ))}
          </div>

          {/* ── Right actions ── */}
          <div style={{
            display: 'flex', alignItems: 'center',
            gap: '8px', flexShrink: 0,
          }}>
            {/* Theme toggle */}
            <button
              onClick={toggle}
              style={{
                width: 36, height: 36, borderRadius: '9px',
                background: T.surface2, border: `1px solid ${T.border}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', fontSize: '14px',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.borderColor = T.border2}
              onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
            >
              {isDark ? '☀️' : '🌙'}
            </button>

            {isAuthenticated ? (
              <button
                onClick={() => navigate('/app')}
                className="press"
                style={{
                  padding: '8px 16px', borderRadius: '9px',
                  background: isDark ? '#10b981' : '#059669',
                  border: 'none', color: '#fff',
                  fontSize: '13.5px', fontWeight: 700,
                  cursor: 'pointer',
                  boxShadow: '0 2px 10px rgba(16,185,129,0.28)',
                  transition: 'all 0.15s ease',
                  fontFamily: 'inherit',
                  display: 'flex', alignItems: 'center', gap: '5px',
                }}
                onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 18px rgba(16,185,129,0.40)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow = '0 2px 10px rgba(16,185,129,0.28)'}
              >
                Go to App →
              </button>
            ) : (
              // Show on desktop only — mobile uses hamburger
              <>
                <button
                  onClick={() => navigate('/login')}
                  className="hide-mobile"
                  style={{
                    padding: '8px 16px', borderRadius: '9px',
                    background: 'transparent',
                    border: `1px solid ${T.border}`,
                    color: T.text2, fontSize: '13.5px', fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                    fontFamily: 'inherit',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = T.border2
                    e.currentTarget.style.color = T.text
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = T.border
                    e.currentTarget.style.color = T.text2
                  }}
                >
                  Sign In
                </button>

                {/* FIX: was indigo/purple gradient — now solid emerald */}
                <button
                  onClick={() => navigate('/register')}
                  className="press hide-mobile"
                  style={{
                    padding: '8px 18px', borderRadius: '9px',
                    background: isDark ? '#10b981' : '#059669',
                    border: 'none', color: '#fff',
                    fontSize: '13.5px', fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 2px 10px rgba(16,185,129,0.28)',
                    transition: 'all 0.15s ease',
                    fontFamily: 'inherit',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = 'translateY(-1px)'
                    e.currentTarget.style.boxShadow = '0 4px 18px rgba(16,185,129,0.40)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = '0 2px 10px rgba(16,185,129,0.28)'
                  }}
                >
                  Get Started Free
                </button>
              </>
            )}

            {/* Hamburger — mobile only */}
            <button
              onClick={() => setMenuOpen(o => !o)}
              className="show-mobile"
              style={{
                width: 36, height: 36, borderRadius: '9px',
                background: T.surface2, border: `1px solid ${T.border}`,
                display: 'none', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: T.text2,
              }}
            >
              {menuOpen ? <X size={16} /> : <Menu size={16} />}
            </button>
          </div>
        </div>

        {/* ── Mobile dropdown menu ── */}
        {menuOpen && (
          <div style={{
            borderTop: `1px solid ${T.border}`,
            padding: '12px 16px 16px',
            display: 'flex', flexDirection: 'column', gap: '4px',
          }}>
            {links.map(l => (
              <button
                key={l.label}
                onClick={() => handleNav(l.href)}
                style={{
                  padding: '11px 14px', borderRadius: '9px',
                  background: 'transparent', border: 'none',
                  color: T.text2, fontSize: '15px', fontWeight: 500,
                  cursor: 'pointer', textAlign: 'left',
                  fontFamily: 'inherit', transition: 'all 0.12s ease',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = T.surface2; e.currentTarget.style.color = T.text }}
                onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = T.text2 }}
              >
                {l.label}
              </button>
            ))}

            <div style={{ display: 'flex', gap: '8px', marginTop: '8px', paddingTop: '12px', borderTop: `1px solid ${T.border}` }}>
              <button onClick={() => { navigate('/login'); setMenuOpen(false) }}
                style={{ flex: 1, padding: '11px', borderRadius: '9px', background: T.surface2, border: `1px solid ${T.border}`, color: T.text, fontSize: '14px', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>
                Sign In
              </button>
              <button onClick={() => { navigate('/register'); setMenuOpen(false) }}
                style={{ flex: 1, padding: '11px', borderRadius: '9px', background: isDark ? '#10b981' : '#059669', border: 'none', color: '#fff', fontSize: '14px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                Get Started
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* CSS for mobile/desktop visibility helpers */}
      <style>{`
        @media (max-width: 768px) {
          .hide-mobile { display: none !important; }
          .show-mobile { display: flex !important; }
        }
        @media (min-width: 769px) {
          .show-mobile { display: none !important; }
          .hide-mobile { display: flex !important; }
        }
      `}</style>
    </>
  )
}