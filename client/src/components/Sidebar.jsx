// client/src/components/Sidebar.jsx

import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FolderOpen,
  FileText, CheckSquare, BarChart2,
  Settings, Mic, Sun, Moon, Wifi, WifiOff
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useEffect, useState } from 'react'
import { getHealth, getStats } from '../api/client'

export default function Sidebar() {
  const { T, isDark, toggle } = useTheme()
  const loc     = useLocation()
  const [online, setOnline]   = useState(null)
  const [stats,  setStats]    = useState(null)

  // Poll backend health every 10s
  useEffect(() => {
    const check = () =>
      getHealth()
        .then(() => setOnline(true))
        .catch(() => setOnline(false))
    check()
    const iv = setInterval(check, 10000)
    return () => clearInterval(iv)
  }, [])

  // Load stats once
  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => {})
  }, [])

  const isActive = (to) =>
    to === '/' ? loc.pathname === '/' : loc.pathname.startsWith(to)

  const NAV = [
    { to: '/',          icon: LayoutDashboard, label: 'Dashboard',    badge: null                        },
    { to: '/upload',    icon: Upload,          label: 'Upload',       badge: null                        },
    { to: '/meetings',  icon: FolderOpen,      label: 'Meetings',     badge: stats?.total_meetings       },
    { to: '/summaries', icon: FileText,        label: 'Summaries',    badge: stats?.total_meetings       },
    { to: '/tasks',     icon: CheckSquare,     label: 'Action Items', badge: stats?.total_actions        },
    { to: '/analytics', icon: BarChart2,       label: 'Analytics',    badge: null                        },
    { to: '/settings',  icon: Settings,        label: 'Settings',     badge: null                        },
  ]

  return (
    <aside style={{
      width: '240px', minHeight: '100vh',
      background: T.sidebarBg,
      borderRight: `1px solid ${T.sidebarBorder}`,
      display: 'flex', flexDirection: 'column',
      position: 'fixed', top: 0, left: 0,
      transition: 'background 0.18s ease, border-color 0.18s ease',
      zIndex: 100,
    }}>

      {/* ── Logo ── */}
      <div style={{
        padding: '22px 20px 18px',
        borderBottom: `1px solid ${T.sidebarBorder}`,
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '10px',
            background: T.btnGrad, boxShadow: T.btnShadow,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0,
          }}>
            <Mic size={18} color="#fff" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{
              fontSize: '16px', fontWeight: 800,
              letterSpacing: '-0.04em', color: T.text, lineHeight: 1.1,
            }}>
              Summly
            </div>
            <div style={{
              fontSize: '10px', fontWeight: 500,
              color: T.text3, letterSpacing: '0.04em', marginTop: '1px',
            }}>
              Meeting Intelligence
            </div>
          </div>
        </div>

        <button
          onClick={toggle}
          style={{
            width: '30px', height: '30px', borderRadius: '8px',
            background: T.toggleBg, border: `1px solid ${T.toggleBorder}`,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: T.toggleColor,
            transition: 'all 0.15s ease', flexShrink: 0,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = T.accent
            e.currentTarget.style.color = T.accent
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = T.toggleBorder
            e.currentTarget.style.color = T.toggleColor
          }}
        >
          {isDark ? <Sun size={13} strokeWidth={2} /> : <Moon size={13} strokeWidth={2} />}
        </button>
      </div>

      {/* ── Backend status ── */}
      <div style={{
        padding: '10px 16px',
        borderBottom: `1px solid ${T.sidebarBorder}`,
        display: 'flex', alignItems: 'center', gap: '8px',
      }}>
        <div style={{
          width: '7px', height: '7px', borderRadius: '50%',
          background: online === null ? T.text4
            : online ? T.success
            : T.danger,
          flexShrink: 0,
          boxShadow: online
            ? `0 0 6px ${T.success}`
            : online === false
              ? `0 0 6px ${T.danger}`
              : 'none',
          transition: 'background 0.3s ease',
        }} />
        <span style={{
          fontSize: '11.5px', fontWeight: 500,
          color: online === null ? T.text4
            : online ? T.success
            : T.danger,
        }}>
          {online === null ? 'Checking...'
            : online ? 'Backend Online'
            : 'Backend Offline'}
        </span>
      </div>

      {/* ── Nav ── */}
      <nav style={{
        flex: 1, padding: '10px 8px',
        display: 'flex', flexDirection: 'column',
        gap: '1px', overflowY: 'auto',
      }}>
        {NAV.map(({ to, icon: Icon, label, badge }) => {
          const active = isActive(to)
          return (
            <NavLink key={to} to={to} style={{ textDecoration: 'none' }}>
              <div
                style={{
                  display: 'flex', alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '9px 12px', borderRadius: '9px',
                  cursor: 'pointer', userSelect: 'none',
                  background: active ? T.navActiveBg : 'transparent',
                  border: `1px solid ${active ? T.navActiveBorder : 'transparent'}`,
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => {
                  if (!active) {
                    e.currentTarget.style.background = T.accentBg
                    e.currentTarget.style.color = T.navHover
                  }
                }}
                onMouseLeave={e => {
                  if (!active) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '11px' }}>
                  <Icon
                    size={17} strokeWidth={active ? 2.3 : 1.8}
                    color={active ? T.navActiveText : T.navColor}
                  />
                  <span style={{
                    fontSize: '14.5px',
                    fontWeight: active ? 650 : 450,
                    color: active ? T.navActiveText : T.navColor,
                    letterSpacing: '-0.01em',
                  }}>
                    {label}
                  </span>
                </div>

                {/* Badge */}
                {badge != null && badge > 0 && (
                  <span style={{
                    minWidth: '20px', height: '20px',
                    padding: '0 6px', borderRadius: '99px',
                    fontSize: '11px', fontWeight: 700,
                    background: active ? T.accent : T.surface3,
                    color: active ? '#fff' : T.text3,
                    display: 'flex', alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.15s ease',
                  }}>
                    {badge}
                  </span>
                )}
              </div>
            </NavLink>
          )
        })}
      </nav>

      {/* ── Footer ── */}
      <div style={{
        padding: '14px 18px',
        borderTop: `1px solid ${T.sidebarBorder}`,
      }}>
        <div style={{ fontSize: '11px', lineHeight: 1.65, color: T.text3, fontWeight: 500 }}>
          Summly v4.0 · Phase 4<br />
          <span style={{ color: T.text4, fontWeight: 400 }}>AI Meeting Intelligence</span>
        </div>
      </div>
    </aside>
  )
}