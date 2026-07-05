// client/src/components/BottomNav.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// Mobile navigation — only visible on screens < 768px.
// Two parts:
//   1. BottomBar  — fixed 5-icon strip at the very bottom
//   2. DrawerMenu — full-height slide-over with all nav items
//
// FIXES IN THIS VERSION:
// ───────────────────────
// FIX 1: Added Workspaces to ALL_ITEMS (drawer menu).
//   The drawer showed all pages except Workspaces — now includes it.
//
// FIX 2: Logo lettermark in the drawer header now uses emerald green.
//   Old: used T.text as the color — in light mode this is black on white,
//   which looked identical to plain text, not a branded logo mark.
//   New: consistent emerald (#10b981 / #059669) matching the sidebar.
//
// FIX 3: Drawer background in light mode was hardcoded to '#0A0A0B' (near-black).
//   This made the drawer appear as a dark overlay even when the app was in
//   light mode. Fixed to isDark-aware background.

import { useState, useEffect } from 'react'
import { createPortal }        from 'react-dom'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FolderOpen,
  CheckSquare, BarChart2, Settings,
  FileText, Menu, X, Sun, Moon,
  Layers, ChevronRight,
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth }  from '../context/AuthContext'
import WorkspaceSwitcher from './WorkspaceSwitcher'
import Logo from './Logo'

// Bottom bar — only the 5 most important pages
const BOTTOM_ITEMS = [
  { to: '/app',           icon: LayoutDashboard, label: 'Home'     },
  { to: '/app/upload',    icon: Upload,          label: 'Upload'   },
  { to: '/app/meetings',  icon: FolderOpen,      label: 'Meetings' },
  { to: '/app/tasks',     icon: CheckSquare,     label: 'Tasks'    },
  { to: '/app/analytics', icon: BarChart2,       label: 'Analytics'},
]

// FIX: Added Workspaces to the drawer menu
const ALL_ITEMS = [
  { to: '/app',            icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/app/upload',     icon: Upload,          label: 'Upload'     },
  { to: '/app/meetings',   icon: FolderOpen,      label: 'Meetings'   },
  { to: '/app/summaries',  icon: FileText,        label: 'Summaries'  },
  { to: '/app/tasks',      icon: CheckSquare,     label: 'Tasks'      },
  { to: '/app/analytics',  icon: BarChart2,       label: 'Analytics'  },
  { to: '/app/workspaces', icon: Layers,          label: 'Workspaces' },
  { to: '/app/settings',   icon: Settings,        label: 'Settings'   },
]

// ── Drawer (full-height slide-over panel) ─────────────────────────────────────
function DrawerMenu({ open, onClose, T, isDark, toggle, user }) {
  const loc      = useLocation()
  const navigate = useNavigate()

  // Close drawer automatically when the user navigates to a new page
  useEffect(() => { onClose() }, [loc.pathname])

  // Escape key closes the drawer
  useEffect(() => {
    if (!open) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Prevent background scroll while drawer is open
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  const initials = user?.full_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'

  // FIX: logo color — emerald in both themes (matches sidebar S lettermark)

  // FIX: drawer background was always '#0A0A0B' regardless of theme
  const drawerBg  = isDark ? '#0A0A0B' : '#ffffff'

  return createPortal(
    <>
      {/* Dark overlay — tapping closes the drawer */}
      <div
        onClick={onClose}
        style={{
          position:    'fixed', inset: 0,
          background:  'rgba(0,0,0,0.65)',
          backdropFilter: 'blur(4px)',
          zIndex:      9998,
          opacity:     open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition:  'opacity 0.22s ease',
        }}
      />

      {/* Slide-in drawer panel */}
      <div style={{
        position:  'fixed',
        top: 0, left: 0, bottom: 0,
        width:     '280px',
        zIndex:    9999,
        // FIX: isDark-aware background
        background: drawerBg,
        borderRight:`1px solid ${T.border}`,
        boxShadow: '8px 0 32px rgba(0,0,0,0.4)',
        // Slide in from left: translateX(-100%) = fully off-screen
        transform:  open ? 'translateX(0)' : 'translateX(-100%)',
        transition: 'transform 0.26s cubic-bezier(0.4,0,0.2,1)',
        display:   'flex',
        flexDirection: 'column',
        overflowY: 'auto',
      }}>

        {/* Drawer header */}
        <div style={{
          display:        'flex', alignItems: 'center', justifyContent: 'space-between',
          padding:        '18px 20px',
          borderBottom:   `1px solid ${T.border}`,
          flexShrink:     0,
        }}>
          {/* Logo mark + wordmark — consolidated into <Logo /> */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Logo size={32} wordmarkSize={18} />
          </div>

          {/* Close × — 44px touch target (was 32px, under the 44px minimum
              for mobile tap targets) */}
          <button
            onClick={onClose}
            aria-label="Close menu"
            style={{
              width: 44, height: 44, borderRadius: '10px',
              background: T.surface2, border: `1px solid ${T.border}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: T.text3,
            }}
          >
            <X size={15} />
          </button>
        </div>

        {/* Workspace switcher — same component/dropdown used everywhere else,
            given a full-width row here since the drawer has room for it. */}
        <div style={{ padding: '14px 14px 4px', flexShrink: 0 }}>
          <WorkspaceSwitcher variant="bar" isDark={isDark} />
        </div>

        {/* Nav items list */}
        <nav style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
          {ALL_ITEMS.map(({ to, icon: Icon, label }) => {
            const active = to === '/app' ? loc.pathname === '/app' : loc.pathname.startsWith(to)
            return (
              <NavLink key={to} to={to} style={{ textDecoration: 'none', display: 'block' }}>
                <div style={{
                  display:      'flex', alignItems: 'center', gap: '12px',
                  padding:      '11px 12px', borderRadius: '10px', marginBottom: '2px',
                  background:   active ? T.navActiveBg || `${T.accent}10` : 'transparent',
                  border:       `1px solid ${active ? (T.navActiveBorder || `${T.accent}30`) : 'transparent'}`,
                  transition:   'all 0.12s ease',
                }}>
                  <Icon
                    size={18}
                    strokeWidth={active ? 2.2 : 1.8}
                    color={active ? T.accent : T.text3}
                  />
                  <span style={{
                    fontSize:   '15px',
                    fontWeight: active ? 600 : 400,
                    color:      active ? T.text : T.text2,
                  }}>
                    {label}
                  </span>
                </div>
              </NavLink>
            )
          })}
        </nav>

        {/* Footer — theme toggle + user */}
        <div style={{
          flexShrink: 0,
          padding:    '14px',
          borderTop:  `1px solid ${T.border}`,
          display:    'flex', flexDirection: 'column', gap: '10px',
        }}>
          {/* Theme toggle */}
          <button
            onClick={toggle}
            style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              padding: '10px 12px', borderRadius: '10px',
              background: T.surface2, border: `1px solid ${T.border}`,
              cursor: 'pointer', color: T.text2,
              fontSize: '14px', fontWeight: 500,
              fontFamily: 'inherit', transition: 'all 0.12s ease', width: '100%',
            }}
          >
            {isDark
              ? <Sun  size={16} color={T.amber} />
              : <Moon size={16} color={T.accent} />
            }
            {isDark ? 'Switch to Light' : 'Switch to Dark'}
          </button>

          {/* User row */}
          {user && (
            <div
              onClick={() => { navigate('/app/settings'); onClose() }}
              role="button"
              tabIndex={0}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/app/settings'); onClose() } }}
              style={{
                display: 'flex', alignItems: 'center', gap: '10px',
                padding: '10px 12px', borderRadius: '10px',
                background: T.surface2, border: `1px solid ${T.border}`,
                cursor: 'pointer',
              }}
            >
              <div style={{
                width: 32, height: 32, borderRadius: '8px', flexShrink: 0,
                background: `linear-gradient(145deg, ${T.accent}, ${T.accentLight})`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontWeight: 800, fontSize: '11px',
              }}>
                {initials}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: '13px', fontWeight: 600, color: T.text,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {user.full_name}
                </div>
                <div style={{
                  fontSize: '11px', color: T.text3,
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {user.email}
                </div>
              </div>
              <ChevronRight size={14} color={T.text3} />
            </div>
          )}
        </div>
      </div>
    </>,
    document.body,
  )
}

// ── Bottom Navigation Bar ─────────────────────────────────────────────────────
export default function BottomNav() {
  const { T, isDark, toggle } = useTheme()
  const { user }              = useAuth()
  const loc                   = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)

  return (
    <>
      {/* Fixed bar at the bottom of the viewport */}
      <div style={{
        position:   'fixed',
        bottom: 0, left: 0, right: 0,
        zIndex:     200,
        // FIX: isDark-aware background — was hardcoded dark even in light mode
        background: isDark ? 'rgba(10,10,11,0.96)' : 'rgba(255,255,255,0.96)',
        backdropFilter:       'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderTop:  `1px solid ${T.border}`,
        display:    'flex', alignItems: 'stretch',
        paddingBottom: 'env(safe-area-inset-bottom)',
        boxShadow:  isDark ? '0 -4px 24px rgba(0,0,0,0.5)' : '0 -4px 24px rgba(0,0,0,0.08)',
      }}>

        {BOTTOM_ITEMS.map(({ to, icon: Icon, label }) => {
          const active = to === '/app' ? loc.pathname === '/app' : loc.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              style={{
                flex: 1, textDecoration: 'none',
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                gap: '3px', padding: '10px 4px',
                transition: 'opacity 0.15s ease',
                opacity: active ? 1 : 0.55,
                minWidth: 0,
              }}
            >
              <div style={{
                width: 32, height: 32, borderRadius: '9px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: active ? `${T.accent}18` : 'transparent',
                transition: 'background 0.15s ease',
              }}>
                <Icon
                  size={19}
                  strokeWidth={active ? 2.2 : 1.8}
                  color={active ? T.accent : T.text3}
                />
              </div>
              <span style={{
                fontSize:   '10px',
                fontWeight: active ? 600 : 400,
                color:      active ? T.accent : T.text3,
                letterSpacing: '0.01em',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                maxWidth: '100%',
              }}>
                {label}
              </span>
            </NavLink>
          )
        })}

        {/* Hamburger button — opens drawer */}
        <button
          onClick={() => setDrawerOpen(true)}
          style={{
            flex: 1, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            gap: '3px', padding: '10px 4px',
            background: 'none', border: 'none',
            cursor: 'pointer', opacity: 0.55,
            fontFamily: 'inherit',
          }}
        >
          <div style={{
            width: 32, height: 32, borderRadius: '9px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Menu size={19} color={T.text3} strokeWidth={1.8} />
          </div>
          <span style={{ fontSize: '10px', fontWeight: 400, color: T.text3 }}>Menu</span>
        </button>
      </div>

      {/* Drawer rendered via portal into document.body */}
      <DrawerMenu
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        T={T}
        isDark={isDark}
        toggle={toggle}
        user={user}
      />
    </>
  )
}