// client/src/components/Sidebar.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// The fixed left sidebar with navigation, workspace switcher, and user footer.
// Collapses to an icon-only rail on tablets (and manually on desktop).
// Hidden on mobile (BottomNav + MobileTopBar take over).
//
// LAYOUT REDESIGN (space + collapse fix):
// ─────────────────────────────────────────
// The workspace switcher used to be a big card (name + a 2x2 stats grid)
// sitting INSIDE the scrollable nav list, wrapped in a block that collapsed
// to `maxHeight: 0` whenever the sidebar itself collapsed. Two problems:
//   1. On tablets (which auto-collapse) and whenever a desktop user manually
//      collapsed the sidebar, the switcher vanished completely — no icon,
//      no indicator, no way to change or even see the active workspace.
//   2. The stats grid duplicated numbers already shown prominently on the
//      Dashboard, permanently costing ~110px of vertical space that could
//      go to actual navigation.
//
// Fix: the switcher is now its own row in the fixed header (always visible,
// never part of the scrolling/collapsing nav), rendered via the shared
// <WorkspaceSwitcher> component — a full pill when expanded, a single
// 30x30 dot button when collapsed. Its dropdown is portalled to <body>,
// so it always escapes the rail's width instead of being clipped.

import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FolderOpen, FileText,
  CheckSquare, BarChart2, Settings, Layers,
  Sun, Moon, Zap, ChevronRight,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react'
import { useTheme }                     from '../ThemeContext'
import { useEffect, useState, useCallback } from 'react'
import { getHealth }                     from '../api/client'
import { useAuth }                       from '../context/AuthContext'
import WorkspaceSwitcher                 from './WorkspaceSwitcher'
import Logo                              from './Logo'

// ── Nav items ─────────────────────────────────────────────────────────────────
// Previously each item had its own hardcoded color (indigo/cyan/purple/blue/
// orange/emerald/violet/amber) — a rainbow sidebar that directly contradicted
// theme.js's own documented brand rule ("one accent color, not six; nav items
// are monochrome, only active uses accent"). Items are distinguished by icon
// shape, not color — active state now uses the single shared accent below.
const NAV = [
  { to: '/app',             icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/app/upload',      icon: Upload,          label: 'Upload'     },
  { to: '/app/meetings',    icon: FolderOpen,      label: 'Meetings'   },
  { to: '/app/summaries',   icon: FileText,        label: 'Summaries'  },
  { to: '/app/tasks',       icon: CheckSquare,     label: 'Tasks'      },
  { to: '/app/analytics',   icon: BarChart2,       label: 'Analytics'  },
  { to: '/app/workspaces',  icon: Layers,          label: 'Workspaces' },
  { to: '/app/settings',    icon: Settings,        label: 'Settings'   },
]

const EW = 248
const CW = 54

// ── Theme-aware color tokens ──────────────────────────────────────────────────
// Rebuilt to derive entirely from the shared theme.js tokens (T) instead of a
// separate, hardcoded indigo/purple palette. This sidebar used to be visually
// disconnected from the rest of the app's emerald brand — this fixes that.
const tokens = (T, isDark) => ({
  sbBg:       T.sidebarBg,
  sbBorder:   T.sidebarBorder,
  sbShadow:   isDark
    ? '4px 0 28px rgba(0,0,0,0.45)'
    : '4px 0 16px rgba(0,0,0,0.06)',

  sectionLabel: T.text3,

  navLabelOff:   T.navColor,
  navLabelHover: T.navHover,
  navLabelOn:    T.navActiveText,

  navRowHoverBg:     isDark ? 'rgba(255,255,255,0.05)' : T.accentBg,
  navRowHoverBorder: isDark ? 'rgba(255,255,255,0.08)' : T.border2,

  iconOff: T.text3,

  wordmark: T.text,

  wsCardBg:     isDark
    ? `linear-gradient(135deg,${T.accentBg},rgba(255,255,255,0.03))`
    : `linear-gradient(135deg,${T.accentBg},rgba(0,0,0,0.02))`,
  wsCardBorder: T.border2,
  wsTitleColor: T.text3,
  wsStatBg:     isDark ? 'rgba(255,255,255,0.05)' : T.accentBg,
  wsStatBorder: T.border,
  wsLabelColor: T.text3,

  footerBorder:  T.border,
  userRowBg:     isDark ? 'rgba(255,255,255,0.04)' : T.accentBg,
  userRowBorder: T.border,
  userName:      T.text,
  userEmail:     T.text3,

  toggleBg:     T.toggleBg,
  toggleBorder: T.toggleBorder,
  toggleColor:  T.toggleColor,

  versionColor: T.text4,

  // "Meeting IQ" badge — was purple/violet, now the single accent
  badgeBg:     T.accentBg,
  badgeBorder: `${T.accent}3d`,
  badgeColor:  T.accent,

  statusOnColor: T.success,

  tooltipBg:     T.surface2,
  tooltipColor:  T.text,
  tooltipBorder: T.border2,
})

// ── Component ─────────────────────────────────────────────────────────────────
export default function Sidebar({ collapsed: cp, setCollapsed: scp } = {}) {
  const { T, isDark, toggle }   = useTheme()
  const { user }             = useAuth()
  const loc                  = useLocation()
  const navigate             = useNavigate()

  const [online,  setOnline]  = useState(null)
  const [hovered, setHovered] = useState(null)

  const [_c, _sc]    = useState(false)
  const collapsed    = cp  !== undefined ? cp  : _c
  const setCollapsed = scp !== undefined ? scp : _sc

  useEffect(() => {
    const check = () => getHealth().then(() => setOnline(true)).catch(() => setOnline(false))
    check()
    const iv = setInterval(check, 10_000)
    return () => clearInterval(iv)
  }, [])

  const isActive = useCallback(
    (to) => to === '/app' ? loc.pathname === '/app' : loc.pathname.startsWith(to),
    [loc.pathname],
  )

  const initials = user?.full_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
  const tk       = tokens(T, isDark)

  return (
    <>
      <style>{`
        .sb-root, .sb-root * {
          font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont,
                       'Segoe UI', system-ui, sans-serif;
          -webkit-font-smoothing: antialiased;
        }
        @keyframes sbPulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.55); }
          60%      { box-shadow: 0 0 0 4px rgba(16,185,129,0); }
        }
        .sb-root {
          transition: width 0.24s cubic-bezier(0.4,0,0.2,1), background 0.20s ease;
          will-change: width;
        }
        .sb-nav-row {
          transition: background 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
        }
        .sb-nav-row:hover .sb-icon { transform: scale(1.08); }
        .sb-icon { transition: transform 0.16s cubic-bezier(0.34,1.56,0.64,1); }
        .sb-btn  { transition: transform 0.14s cubic-bezier(0.34,1.56,0.64,1), background 0.12s ease; }
        .sb-btn:hover { transform: scale(1.09); }
        .sb-fade {
          transition: opacity 0.18s ease, max-width 0.22s cubic-bezier(0.4,0,0.2,1);
          overflow: hidden; white-space: nowrap;
        }
        .sb-fade-h {
          transition: opacity 0.16s ease, max-height 0.20s ease;
          overflow: hidden;
        }
        .sb-tip {
          position: absolute;
          left: calc(100% + 10px);
          top: 50%; transform: translateY(-50%);
          padding: 4px 10px; border-radius: 7px;
          font-size: 12px; font-weight: 600;
          white-space: nowrap; pointer-events: none;
          opacity: 0; transition: opacity 0.13s ease; z-index: 300;
          box-shadow: 0 4px 14px rgba(0,0,0,0.18);
          background: ${tk.tooltipBg};
          color: ${tk.tooltipColor};
          border: 1px solid ${tk.tooltipBorder};
        }
        .sb-nav-row:hover .sb-tip { opacity: 1; }
        .sb-nav-scroll {
          overflow-y: auto; overflow-x: hidden; scrollbar-width: none;
        }
        .sb-nav-scroll::-webkit-scrollbar { display: none; }
      `}</style>

      <aside
        className="sb-root"
        style={{
          width:         collapsed ? `${CW}px` : `${EW}px`,
          height:        '100vh',
          position:      'fixed',
          top: 0, left: 0,
          zIndex:        100,
          display:       'flex',
          flexDirection: 'column',
          overflow:      'hidden',
          background:    tk.sbBg,
          borderRight:   `1.5px solid ${tk.sbBorder}`,
          boxShadow:     tk.sbShadow,
        }}
      >

        {/* ── HEADER ── */}
        <div style={{
          flexShrink:  0,
          zIndex:      1,
          position:    'relative',
          padding:     collapsed ? '10px 8px' : '10px 12px 9px',
          borderBottom:`1px solid ${tk.sbBorder}`,
        }}>

          {/* Row 1: logo · wordmark · theme toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: collapsed ? 0 : '7px' }}>

            {/* Logo — consolidated into <Logo />, see components/Logo.jsx */}
            <Logo variant="icon" size={34} onClick={() => navigate('/app')} />

            {/* FIX: wordmark uses explicit tk.wordmark color, not undefined CSS variable */}
            <div
              className="sb-fade"
              style={{
                fontSize:      '22px',
                fontWeight:    800,
                letterSpacing: '-0.07em',
                lineHeight:    1,
                flex:          1,
                maxWidth:      collapsed ? '0px' : '150px',
                opacity:       collapsed ? 0 : 1,
                color:         tk.wordmark,
              }}
            >
              Summly
            </div>

            {/* Theme toggle — expanded only */}
            {!collapsed && (
              <button
                onClick={toggle}
                className="sb-btn"
                title={isDark ? 'Light mode' : 'Dark mode'}
                style={{
                  width: '30px', height: '30px', borderRadius: '9px', flexShrink: 0,
                  background: isDark ? 'rgba(255,255,255,0.05)' : T.accentBg,
                  border: `1px solid ${isDark ? 'rgba(255,255,255,0.09)' : T.border2}`,
                  cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                {isDark
                  ? <Sun  size={13} strokeWidth={2} color={T.amber} />
                  : <Moon size={13} strokeWidth={2} color={T.accent} />
                }
              </button>
            )}
          </div>

          {/* Row 2: AI badge + status */}
          <div
            className="sb-fade-h"
            style={{
              maxHeight: collapsed ? '0px' : '24px',
              opacity:   collapsed ? 0 : 1,
              display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden',
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center', gap: '4px',
              padding: '2px 7px', borderRadius: '99px', flexShrink: 0,
              background: tk.badgeBg,
              border: `1px solid ${tk.badgeBorder}`,
            }}>
              <Zap size={7} color={tk.badgeColor} fill={tk.badgeColor} />
              <span style={{
                fontSize: '9px', fontWeight: 700,
                color: tk.badgeColor,
                textTransform: 'uppercase', letterSpacing: '0.09em',
                whiteSpace: 'nowrap',
              }}>
                Meeting IQ
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto', flexShrink: 0 }}>
              <div style={{
                width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
                background: online === null
                  ? (isDark ? 'rgba(255,255,255,0.22)' : T.text4)
                  : online ? '#10b981' : '#ef4444',
                animation: online ? 'sbPulse 2.4s ease infinite' : 'none',
              }} />
              <span style={{
                fontSize: '9px', fontWeight: 700, letterSpacing: '0.02em',
                fontFamily: 'monospace',
                color: online === null
                  ? (isDark ? 'rgba(255,255,255,0.30)' : T.text4)
                  : online ? tk.statusOnColor : '#f87171',
              }}>
                {online === null ? '…' : online ? 'Live' : 'Off'}
              </span>
            </div>
          </div>

          {/* Row 3: Workspace switcher — lives in the fixed header (not the
              scrollable/collapsible nav), so it's always visible and always
              clickable in both expanded and collapsed states. This is the
              fix for the switcher disappearing entirely on collapse. */}
          <div style={{ marginTop: collapsed ? '8px' : '8px' }}>
            <WorkspaceSwitcher variant={collapsed ? 'icon' : 'bar'} isDark={isDark} />
          </div>
        </div>

        {/* ── NAV ── */}
        <nav style={{
          flex: 1, minHeight: 0,
          position: 'relative', zIndex: 1,
          display: 'flex', flexDirection: 'column',
          padding: collapsed ? '6px 5px' : '6px 8px',
        }}>

          {/* MENU label */}
          <div style={{
            padding:       collapsed ? '4px 0 4px' : '3px 5px 5px',
            fontSize:      '9px',
            fontWeight:    700,
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            color:         tk.sectionLabel,
            textAlign:     collapsed ? 'center' : 'left',
            opacity:       collapsed ? 0 : 1,
            maxHeight:     collapsed ? '0px' : '22px',
            overflow:      'hidden',
            transition:    'opacity 0.16s ease',
          }}>
            Menu
          </div>

          {/* Scrollable nav list */}
          <div className="sb-nav-scroll" style={{ flex: 1, minHeight: 0 }}>
            {NAV.map(({ to, icon: Icon, label }) => {
              const active = isActive(to)
              const hov    = hovered === to

              return (
                <NavLink key={to} to={to} style={{ textDecoration: 'none', display: 'block' }}>
                  <div
                    className="sb-nav-row"
                    onMouseEnter={() => setHovered(to)}
                    onMouseLeave={() => setHovered(null)}
                    style={{
                      position: 'relative',
                      display: 'flex', alignItems: 'center',
                      gap:     collapsed ? 0 : '9px',
                      padding: collapsed ? '8px 0' : '7px 8px',
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      borderRadius: '9px',
                      marginBottom: '1px',
                      cursor: 'pointer', userSelect: 'none',
                      // Single shared accent, subtle tint only — no per-item
                      // rainbow, no glow shadow. The hairline left bar below
                      // is the active indicator; the fill is just a whisper.
                      background: active ? T.accentBg : hov ? tk.navRowHoverBg : 'transparent',
                      border: '1px solid transparent',
                    }}
                  >
                    {/* Hairline active indicator — thin left bar, no glow */}
                    {active && !collapsed && (
                      <div style={{
                        position: 'absolute', left: 0, top: '20%', bottom: '20%',
                        width: '2px', borderRadius: '0 2px 2px 0',
                        background: T.accent,
                      }} />
                    )}

                    {/* Icon box — collapsed rail hides the hairline bar, so
                        active state gets a subtle ring here instead, to keep
                        wayfinding when the sidebar is collapsed. */}
                    <div
                      className="sb-icon"
                      style={{
                        width: '28px', height: '28px', borderRadius: '8px', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'transparent',
                        boxShadow: active && collapsed ? `0 0 0 1.5px ${T.accent}55` : 'none',
                        transition: 'background 0.12s ease, box-shadow 0.12s ease',
                      }}
                    >
                      <Icon
                        size={14}
                        strokeWidth={active ? 2.3 : 1.9}
                        color={active ? T.accent : hov ? T.text2 : tk.iconOff}
                        style={{ transition: 'color 0.12s ease' }}
                      />
                    </div>

                    {/* Label */}
                    <span
                      className="sb-fade"
                      style={{
                        flex:          1,
                        maxWidth:      collapsed ? '0px' : '150px',
                        opacity:       collapsed ? 0 : 1,
                        fontSize:      '13px',
                        fontWeight:    active ? 650 : 450,
                        letterSpacing: '-0.01em',
                        lineHeight:    1.25,
                        color:         active ? tk.navLabelOn : hov ? tk.navLabelHover : tk.navLabelOff,
                        transition:    'color 0.12s ease',
                      }}
                    >
                      {label}
                    </span>

                    {/* Tooltip — collapsed only */}
                    {collapsed && <span className="sb-tip">{label}</span>}
                  </div>
                </NavLink>
              )
            })}
          </div>

        </nav>

        {/* ── FOOTER ── */}
        <div style={{
          flexShrink: 0, zIndex: 1, position: 'relative',
          padding:    collapsed ? '7px 5px' : '7px 10px',
          borderTop:  `1px solid ${tk.footerBorder}`,
          display: 'flex', flexDirection: 'column', gap: '5px',
        }}>
          {/* User row */}
          {user && (
            <div
              title={collapsed ? `${user.full_name} · ${user.email}` : undefined}
              onClick={() => navigate('/app/settings')}
              role="button"
              tabIndex={0}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/app/settings') } }}
              style={{
                display: 'flex', alignItems: 'center',
                gap:     collapsed ? 0 : '8px',
                padding: collapsed ? '6px 0' : '6px 8px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                borderRadius: '9px',
                background: tk.userRowBg,
                border:     `1px solid ${tk.userRowBorder}`,
                cursor: 'pointer', transition: 'all 0.12s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background  = isDark ? 'rgba(255,255,255,0.08)' : T.accentBg
                e.currentTarget.style.borderColor = T.border2
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background  = tk.userRowBg
                e.currentTarget.style.borderColor = tk.userRowBorder
              }}
            >
              <div style={{
                width: '28px', height: '28px', borderRadius: '8px', flexShrink: 0,
                background: `linear-gradient(145deg,${T.accent},${T.accentLight})`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontWeight: 800, fontSize: '10px',
                letterSpacing: '-0.02em',
                boxShadow: `0 3px 8px ${T.accent}44`,
              }}>
                {initials}
              </div>

              <div
                className="sb-fade"
                style={{
                  flex: 1, minWidth: 0, overflow: 'hidden',
                  maxWidth: collapsed ? '0px' : '130px',
                  opacity:  collapsed ? 0 : 1,
                }}
              >
                <div style={{
                  fontSize: '12px', fontWeight: 650, color: tk.userName,
                  letterSpacing: '-0.02em',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {user.full_name}
                </div>
                <div style={{
                  fontSize: '10px', fontWeight: 400, color: tk.userEmail, marginTop: '1px',
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {user.email || 'Pro Member'}
                </div>
              </div>

              {!collapsed && (
                <ChevronRight
                  size={11} strokeWidth={2.5}
                  color={isDark ? 'rgba(255,255,255,0.28)' : T.text4}
                  style={{ flexShrink: 0 }}
                />
              )}
            </div>
          )}

          {/* Collapse toggle */}
          <button
            onClick={() => setCollapsed(c => !c)}
            className="sb-btn"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{
              width: '100%', height: '30px', borderRadius: '8px',
              background: tk.toggleBg,
              border:     `1px solid ${tk.toggleBorder}`,
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
              color: tk.toggleColor,
            }}
          >
            {collapsed
              ? <PanelLeftOpen  size={13} strokeWidth={2} />
              : <PanelLeftClose size={13} strokeWidth={2} />
            }
            {!collapsed && (
              <span style={{ fontSize: '11px', fontWeight: 600, color: tk.toggleColor }}>
                Collapse
              </span>
            )}
          </button>

          {!collapsed && (
            <div style={{
              textAlign:   'center',
              fontSize:    '9px',
              color:       tk.versionColor,
              fontFamily:  'monospace',
              letterSpacing: '0.04em',
            }}>
              v4.0 · AI Meeting Intelligence
            </div>
          )}
        </div>
      </aside>
    </>
  )
}