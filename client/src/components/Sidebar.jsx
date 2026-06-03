import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Upload, FolderOpen, FileText,
  CheckSquare, BarChart2, Settings, BrainCircuit,
  Sun, Moon, Zap, ChevronRight, ChevronDown, PanelLeftClose, PanelLeftOpen,
} from 'lucide-react'
import { useTheme }  from '../ThemeContext'
import { useEffect, useState, useCallback } from 'react'
import { getHealth, getStats } from '../api/client'
import { useAuth }   from '../context/AuthContext'

/* ─── nav items ──────────────────────────────────────────────────────────── */
const NAV = [
  { to: '/app',           icon: LayoutDashboard, label: 'Dashboard',    color: '#6366f1', glow: 'rgba(99,102,241,0.50)'  },
  { to: '/app/upload',    icon: Upload,          label: 'Upload',       color: '#06b6d4', glow: 'rgba(6,182,212,0.50)'   },
  { to: '/app/meetings',  icon: FolderOpen,      label: 'Meetings',     color: '#a855f7', glow: 'rgba(168,85,247,0.50)'  },
  { to: '/app/summaries', icon: FileText,        label: 'Summaries',    color: '#3b82f6', glow: 'rgba(59,130,246,0.50)'  },
  { to: '/app/tasks',     icon: CheckSquare,     label: 'Action Items', color: '#f97316', glow: 'rgba(249,115,22,0.50)'  },
  { to: '/app/analytics', icon: BarChart2,       label: 'Analytics',    color: '#10b981', glow: 'rgba(16,185,129,0.50)'  },
  { to: '/app/settings',  icon: Settings,        label: 'Settings',     color: '#f59e0b', glow: 'rgba(245,158,11,0.50)'  },
]

const WS_STATS = (s) => [
  { label: 'Meetings',  value: s?.total_meetings  ?? 0, color: '#818cf8' },
  { label: 'Decisions', value: s?.total_decisions ?? 0, color: '#c084fc' },
  { label: 'Tasks',     value: s?.total_actions   ?? 0, color: '#fb923c' },
  { label: 'Topics',    value: s?.total_topics    ?? 0, color: '#22d3ee' },
]

const EW = 248   // expanded width px
const CW = 54    // collapsed rail px

/* ─── theme-aware color tokens ───────────────────────────────────────────── */
// These replace all the scattered rgba calls with named, readable constants.
// LIGHT theme deliberately uses near-black values for crisp readability.
const tokens = (isDark) => ({
  // Sidebar surface
  sbBg:       isDark ? '#111018'             : '#ffffff',
  sbBorder:   isDark ? 'rgba(99,102,241,0.20)' : 'rgba(99,102,241,0.22)',
  sbShadow:   isDark
    ? '4px 0 28px rgba(0,0,0,0.55), 1px 0 0 rgba(99,102,241,0.14)'
    : '4px 0 20px rgba(99,102,241,0.10), 1px 0 0 rgba(99,102,241,0.14)',

  // Section label (MENU, WORKSPACE)
  sectionLabel: isDark ? 'rgba(255,255,255,0.30)' : '#6b6b80',

  // Nav label — INACTIVE
  navLabelOff:  isDark ? 'rgba(255,255,255,0.50)' : '#3d3d5c',
  // Nav label — HOVER
  navLabelHover: isDark ? 'rgba(255,255,255,0.82)' : '#1a1a2e',
  // Nav label — ACTIVE  (fully opaque, guaranteed visible)
  navLabelOn:   isDark ? '#ffffff'                 : '#1a1a2e',

  // Nav row background hover
  navRowHoverBg:     isDark ? 'rgba(255,255,255,0.05)' : 'rgba(99,102,241,0.06)',
  navRowHoverBorder: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(99,102,241,0.14)',

  // Nav icon inactive color
  iconOff: isDark ? 'rgba(255,255,255,0.42)' : '#5a5a78',

  // Workspace card
  wsCardBg:     isDark
    ? 'linear-gradient(135deg,rgba(99,102,241,0.10),rgba(168,85,247,0.06))'
    : 'linear-gradient(135deg,rgba(99,102,241,0.07),rgba(124,58,237,0.04))',
  wsCardBorder: isDark ? 'rgba(99,102,241,0.18)' : 'rgba(99,102,241,0.16)',
  wsTitleColor: isDark ? 'rgba(255,255,255,0.32)' : '#6b6b80',
  wsStatBg:     isDark ? 'rgba(255,255,255,0.05)' : 'rgba(99,102,241,0.05)',
  wsStatBorder: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(99,102,241,0.10)',
  wsLabelColor: isDark ? 'rgba(255,255,255,0.38)' : '#5a5a78',

  // Footer / user row
  footerBorder: isDark ? 'rgba(99,102,241,0.14)' : 'rgba(99,102,241,0.14)',
  userRowBg:    isDark ? 'rgba(255,255,255,0.04)' : 'rgba(99,102,241,0.05)',
  userRowBorder:isDark ? 'rgba(255,255,255,0.08)' : 'rgba(99,102,241,0.12)',
  userName:     isDark ? 'rgba(255,255,255,0.92)' : '#1a1a2e',
  userEmail:    isDark ? 'rgba(255,255,255,0.42)' : '#5a5a78',

  // Toggle button
  toggleBg:     isDark ? 'rgba(99,102,241,0.12)' : 'rgba(99,102,241,0.08)',
  toggleBorder: isDark ? 'rgba(99,102,241,0.26)' : 'rgba(99,102,241,0.20)',
  toggleColor:  isDark ? '#a5b4fc'               : '#4f46e5',

  // Version text
  versionColor: isDark ? 'rgba(255,255,255,0.18)' : '#9999b3',

  // Logo tagline badge
  badgeBg:      isDark ? 'rgba(168,85,247,0.13)' : 'rgba(124,58,237,0.08)',
  badgeBorder:  isDark ? 'rgba(168,85,247,0.24)' : 'rgba(124,58,237,0.18)',
  badgeColor:   isDark ? '#c084fc'               : '#6d28d9',

  // Status
  statusOnColor: isDark ? '#34d399' : '#059669',

  // Tooltip
  tooltipBg:     isDark ? '#1e1b2e' : '#ffffff',
  tooltipColor:  isDark ? '#e2e0ff' : '#3730a3',
  tooltipBorder: isDark ? 'rgba(99,102,241,0.32)' : 'rgba(99,102,241,0.22)',
})

/* ─── component ──────────────────────────────────────────────────────────── */
export default function Sidebar({ collapsed: cp, setCollapsed: scp } = {}) {
  const { isDark, toggle }       = useTheme()
  const { user }                 = useAuth()
  const loc                      = useLocation()
  const navigate                 = useNavigate()
  const [workspaceOpen, setWorkspaceOpen] = useState(true)

  const [online,  setOnline]  = useState(null)
  const [stats,   setStats]   = useState(null)
  const [hovered, setHovered] = useState(null)

  // Lifted state (syncs main-content margin) or local fallback
  const [_c, _sc]      = useState(false)
  const collapsed      = cp  !== undefined ? cp  : _c
  const setCollapsed   = scp !== undefined ? scp : _sc

  useEffect(() => {
    const check = () => getHealth().then(() => setOnline(true)).catch(() => setOnline(false))
    check(); const iv = setInterval(check, 10_000); return () => clearInterval(iv)
  }, [])

  useEffect(() => { getStats().then(setStats).catch(() => {}) }, [])

  const isActive = useCallback(
    (to) => to === '/app' ? loc.pathname === '/app' : loc.pathname.startsWith(to),
    [loc.pathname]
  )

  const initials = user?.full_name?.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
  const tk = tokens(isDark)

  return (
    <>
      <style>{`
        /* ── font stack for the entire sidebar ── */
        .sb-root, .sb-root * {
          font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont,
                       'Segoe UI', system-ui, sans-serif;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }

        @keyframes sbPulse {
          0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.55); }
          60%      { box-shadow: 0 0 0 4px rgba(16,185,129,0); }
        }
        @keyframes sbShimmer {
          0%   { background-position: -300% center; }
          100% { background-position:  300% center; }
        }
        @keyframes sbFloat {
          0%,100% { opacity: 0.4;  transform: scale(1);    }
          50%      { opacity: 0.75; transform: scale(1.08); }
        }

        /* sidebar slide transition */
        .sb-root {
          transition:
            width        0.24s cubic-bezier(0.4,0,0.2,1),
            background   0.20s ease,
            box-shadow   0.20s ease;
          will-change: width;
        }

        /* nav row hover */
        .sb-nav-row {
          transition: background 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
        }
        .sb-nav-row:hover .sb-icon { transform: scale(1.08); }
        .sb-icon { transition: transform 0.16s cubic-bezier(0.34,1.56,0.64,1); }

        /* theme + toggle btns */
        .sb-btn { transition: transform 0.14s cubic-bezier(0.34,1.56,0.64,1), background 0.12s ease; }
        .sb-btn:hover { transform: scale(1.09); }

        /* smooth label / content fade on collapse */
        .sb-fade {
          transition: opacity 0.18s ease, max-width 0.22s cubic-bezier(0.4,0,0.2,1);
          overflow: hidden; white-space: nowrap;
        }
        .sb-fade-h {
          transition: opacity 0.16s ease, max-height 0.20s ease;
          overflow: hidden;
        }

        /* tooltip shown on collapsed hover */
        .sb-tip {
          position: absolute;
          left: calc(100% + 10px);
          top: 50%; transform: translateY(-50%);
          padding: 4px 10px;
          border-radius: 7px;
          font-size: 12px; font-weight: 600;
          white-space: nowrap;
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.13s ease;
          z-index: 300;
          box-shadow: 0 4px 14px rgba(0,0,0,0.18);
          background: ${tk.tooltipBg};
          color: ${tk.tooltipColor};
          border: 1px solid ${tk.tooltipBorder};
        }
        .sb-nav-row:hover .sb-tip { opacity: 1; }

        /* wordmark shimmer */
        .sb-wordmark {
          background: linear-gradient(110deg,#818cf8 0%,#c084fc 38%,#67e8f9 72%,#818cf8 100%);
          background-size: 300% auto;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          animation: sbShimmer 5.5s linear infinite;
        }

        /* scrollable nav items — only the items list scrolls, never the whole sidebar */
        .sb-nav-scroll {
          overflow-y: auto;
          overflow-x: hidden;
          /* hide scrollbar visually but keep scroll */
          scrollbar-width: none;
        }
        .sb-nav-scroll::-webkit-scrollbar { display: none; }
      `}</style>

      <aside
        className="sb-root"
        style={{
          width:     collapsed ? `${CW}px` : `${EW}px`,
          height:    '100vh',
          position:  'fixed',
          top: 0, left: 0,
          zIndex:    100,
          display:   'flex',
          flexDirection: 'column',
          overflow:  'hidden',
          background: tk.sbBg,
          borderRight: `1.5px solid ${tk.sbBorder}`,
          boxShadow: tk.sbShadow,
        }}
      >

        {/* ambient glows — decorative only */}
        <div style={{
          position:'absolute',top:'-50px',left:'-25px',width:'170px',height:'170px',
          borderRadius:'50%',pointerEvents:'none',zIndex:0,
          background:'radial-gradient(circle,rgba(99,102,241,0.11) 0%,transparent 65%)',
          animation:'sbFloat 6s ease-in-out infinite',
        }}/>
        <div style={{
          position:'absolute',bottom:'90px',right:'-45px',width:'140px',height:'140px',
          borderRadius:'50%',pointerEvents:'none',zIndex:0,
          background:'radial-gradient(circle,rgba(168,85,247,0.07) 0%,transparent 65%)',
          animation:'sbFloat 8s ease-in-out infinite reverse',
        }}/>

        {/* ══════════════════════════════════════
             HEADER — logo + toggle + tagline
        ══════════════════════════════════════ */}
        <div style={{
          flexShrink:  0,
          zIndex:      1,
          position:    'relative',
          padding:     collapsed ? '10px 8px' : '10px 12px 9px',
          borderBottom:`1px solid ${tk.sbBorder}`,
          background:  isDark
            ? 'linear-gradient(180deg,rgba(99,102,241,0.06) 0%,transparent 100%)'
            : 'linear-gradient(180deg,rgba(80,70,228,0.04) 0%,transparent 100%)',
        }}>

          {/* Row 1: brain · wordmark · theme btn */}
          <div style={{ display:'flex', alignItems:'center', gap:'8px', marginBottom: collapsed ? 0 : '7px' }}>

            {/* Brain icon button */}
            <div
              onClick={() => navigate('/app')}
              style={{
                width:'34px', height:'34px', borderRadius:'11px', flexShrink:0,
                background:'linear-gradient(145deg,#5b5ef4 0%,#a855f7 55%,#06b6d4 100%)',
                display:'flex', alignItems:'center', justifyContent:'center',
                boxShadow:'0 5px 16px rgba(99,102,241,0.45), inset 0 0 0 1px rgba(255,255,255,0.10)',
                cursor:'pointer', position:'relative',
              }}
            >
              <BrainCircuit size={19} color="#fff" strokeWidth={1.9}/>
              {/* glass highlight */}
              <div style={{
                position:'absolute', top:2, left:2, right:'46%', bottom:'46%',
                borderRadius:'8px 8px 2px 2px',
                background:'linear-gradient(140deg,rgba(255,255,255,0.27),transparent)',
                pointerEvents:'none',
              }}/>
            </div>

            {/* Wordmark — fades out on collapse */}
            <div
              className="sb-wordmark sb-fade"
              style={{
                fontSize:'22px', fontWeight:800, letterSpacing:'-0.07em', lineHeight:1,
                flex:1,
                maxWidth: collapsed ? '0px' : '150px',
                opacity:  collapsed ? 0 : 1,
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
                  width:'30px', height:'30px', borderRadius:'9px', flexShrink:0,
                  background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(99,102,241,0.07)',
                  border:`1px solid ${isDark ? 'rgba(255,255,255,0.09)' : 'rgba(99,102,241,0.14)'}`,
                  cursor:'pointer',
                  display:'flex', alignItems:'center', justifyContent:'center',
                }}
              >
                {isDark
                  ? <Sun  size={13} strokeWidth={2}   color="#f59e0b"/>
                  : <Moon size={13} strokeWidth={2}   color="#4f46e5"/>
                }
              </button>
            )}
          </div>

          {/* Row 2: tagline badge + status — collapses away */}
          <div
            className="sb-fade-h"
            style={{
              maxHeight: collapsed ? '0px' : '24px',
              opacity:   collapsed ? 0 : 1,
              display:'flex', alignItems:'center', gap:'6px', overflow:'hidden',
            }}
          >
            {/* AI badge — shortened so it NEVER wraps */}
            <div style={{
              display:'flex', alignItems:'center', gap:'4px',
              padding:'2px 7px', borderRadius:'99px', flexShrink:0,
              background: tk.badgeBg,
              border:`1px solid ${tk.badgeBorder}`,
            }}>
              <Zap size={7} color={tk.badgeColor} fill={tk.badgeColor}/>
              <span style={{
                fontSize:'9px', fontWeight:700,
                color: tk.badgeColor,
                textTransform:'uppercase', letterSpacing:'0.09em',
                whiteSpace:'nowrap',
              }}>
                Meeting IQ
              </span>
            </div>

            {/* Live status */}
            <div style={{ display:'flex', alignItems:'center', gap:'4px', marginLeft:'auto', flexShrink:0 }}>
              <div style={{
                width:'6px', height:'6px', borderRadius:'50%', flexShrink:0,
                background: online === null ? (isDark ? 'rgba(255,255,255,0.22)' : '#9999b3')
                          : online ? '#10b981' : '#ef4444',
                animation: online ? 'sbPulse 2.4s ease infinite' : 'none',
              }}/>
              <span style={{
                fontSize:'9px', fontWeight:700, letterSpacing:'0.02em',
                fontFamily:'monospace',
                color: online === null ? (isDark ? 'rgba(255,255,255,0.30)' : '#9999b3')
                     : online ? tk.statusOnColor : '#f87171',
              }}>
                {online === null ? '…' : online ? 'Live' : 'Off'}
              </span>
            </div>
          </div>
        </div>

        {/* ══════════════════════════════════════
             NAV — scrollable list, flex:1
             CRITICAL: flex:1 + minHeight:0 ensures
             nav never pushes footer off screen
        ══════════════════════════════════════ */}
        <nav style={{
          flex:1, minHeight:0, // ← DO NOT REMOVE minHeight:0
          position:'relative', zIndex:1,
          display:'flex', flexDirection:'column',
          padding: collapsed ? '6px 5px' : '6px 8px',
        }}>

          {/* MENU label */}
          <div style={{
            padding: collapsed ? '4px 0 4px' : '3px 5px 5px',
            fontSize:'9px', fontWeight:700,
            letterSpacing:'0.16em', textTransform:'uppercase',
            color: tk.sectionLabel,
            textAlign: collapsed ? 'center' : 'left',
            transition:'opacity 0.16s ease',
            opacity: collapsed ? 0 : 1,
            maxHeight: collapsed ? '0px' : '22px',
            overflow:'hidden',
          }}>
            Menu
          </div>

          {/* ── scrollable nav list ── */}
          <div className="sb-nav-scroll" style={{ flex:1, minHeight:0 }}>
            {NAV.map(({ to, icon: Icon, label, color, glow }) => {
              const active  = isActive(to)
              const hov     = hovered === to

              return (
                <NavLink key={to} to={to} style={{ textDecoration:'none', display:'block' }}>
                  <div
                    className="sb-nav-row"
                    onMouseEnter={() => setHovered(to)}
                    onMouseLeave={() => setHovered(null)}
                    style={{
                      position:'relative',
                      display:'flex', alignItems:'center',
                      gap: collapsed ? 0 : '9px',
                      padding: collapsed ? '8px 0' : '7px 8px',
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      borderRadius:'9px',
                      marginBottom:'1px',
                      cursor:'pointer', userSelect:'none',
                      background: active
                        ? isDark
                          ? `linear-gradient(135deg,${color}1e 0%,${color}0c 100%)`
                          : `${color}13`
                        : hov
                          ? tk.navRowHoverBg
                          : 'transparent',
                      border:`1px solid ${
                        active ? `${color}3d`
                        : hov   ? tk.navRowHoverBorder
                        :         'transparent'
                      }`,
                      boxShadow: active ? `0 2px 10px ${color}16` : 'none',
                    }}
                  >
                    {/* left accent bar */}
                    {active && !collapsed && (
                      <div style={{
                        position:'absolute', left:0, top:'16%', bottom:'16%',
                        width:'3px', borderRadius:'0 3px 3px 0',
                        background:color, boxShadow:`0 0 8px ${glow}`,
                      }}/>
                    )}

                    {/* icon box */}
                    <div
                      className="sb-icon"
                      style={{
                        width:'28px', height:'28px', borderRadius:'8px', flexShrink:0,
                        display:'flex', alignItems:'center', justifyContent:'center',
                        background: active ? `${color}22` : hov ? `${color}12` : 'transparent',
                        boxShadow: active && collapsed ? `0 0 0 2px ${color}55` : 'none',
                        transition:'background 0.12s ease, box-shadow 0.12s ease',
                      }}
                    >
                      <Icon
                        size={14}
                        strokeWidth={active ? 2.3 : 1.9}
                        color={active ? color : hov ? color + 'dd' : tk.iconOff}
                        style={{ transition:'color 0.12s ease' }}
                      />
                    </div>

                    {/* label — fades on collapse */}
                    <span
                      className="sb-fade"
                      style={{
                        flex:1,
                        maxWidth: collapsed ? '0px' : '150px',
                        opacity:  collapsed ? 0 : 1,
                        // ── FONT: crisp, dark, readable ──
                        fontSize:      '13px',
                        fontWeight:    active ? 650 : 450,
                        letterSpacing: '-0.01em',
                        lineHeight:    1.25,
                        color: active ? tk.navLabelOn : hov ? tk.navLabelHover : tk.navLabelOff,
                        transition:'color 0.12s ease',
                      }}
                    >
                      {label}
                    </span>

                    {/* active dot */}
                    {active && !collapsed && (
                      <div style={{
                        width:'5px', height:'5px', borderRadius:'50%', flexShrink:0,
                        background:color, boxShadow:`0 0 6px ${color}`,
                      }}/>
                    )}

                    {/* tooltip — collapsed only */}
                    {collapsed && <span className="sb-tip">{label}</span>}
                  </div>
                </NavLink>
              )
            })}
          </div>

          {/* ── WORKSPACE STATS ── pinned below nav list, above footer */}
          <div
            className="sb-fade-h"
            style={{
              maxHeight: collapsed ? '0px' : '160px',
              opacity:   collapsed ? 0 : 1,
              paddingTop:'6px',
              flexShrink:0,
            }}
          >
            <div style={{
              padding:'8px 10px', borderRadius:'10px',
              background: tk.wsCardBg,
              border:`1px solid ${tk.wsCardBorder}`,
            }}>
              {/* Workspace title */}
              <div
                onClick={() => setWorkspaceOpen(v => !v)}
                style={{
                  display:'flex',
                  alignItems:'center',
                  justifyContent:'space-between',
                  cursor:'pointer',
                  marginBottom:'6px',
                }}
              >
                <span
                  style={{
                    fontSize:'9px',
                    fontWeight:700,
                    letterSpacing:'0.14em',
                    textTransform:'uppercase',
                    color: tk.wsTitleColor,
                  }}
                >
                  Workspace
                </span>

                <ChevronDown
                  size={12}
                  style={{
                    color: tk.wsTitleColor,
                    transform: workspaceOpen
                      ? 'rotate(0deg)'
                      : 'rotate(-90deg)',
                    transition: 'transform 0.2s ease',
                  }}
                />
              </div>

              {/* 2×2 stat grid */}
              <div
                style={{
                  maxHeight: workspaceOpen ? '200px' : '0px',
                  opacity: workspaceOpen ? 1 : 0,
                  overflow: 'hidden',
                  transition: 'max-height 0.25s ease, opacity 0.2s ease',
                }}
              >
                <div
                  style={{
                    display:'grid',
                    gridTemplateColumns:'1fr 1fr',
                    gap:'4px',
                  }}
                >
                  {WS_STATS(stats).map(s => (
                    <div
                      key={s.label}
                      style={{
                        padding:'5px 7px',
                        borderRadius:'7px',
                        background: tk.wsStatBg,
                        border:`1px solid ${tk.wsStatBorder}`,
                      }}
                    >
                      <div
                        style={{
                          fontSize:'15px',
                          fontWeight:800,
                          letterSpacing:'-0.04em',
                          lineHeight:1,
                          color:s.color,
                        }}
                      >
                        {s.value}
                      </div>

                      <div
                        style={{
                          fontSize:'9.5px',
                          fontWeight:500,
                          color: tk.wsLabelColor,
                          marginTop:'2px',
                        }}
                      >
                        {s.label}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* ══════════════════════════════════════
             FOOTER — user + collapse toggle + version
        ══════════════════════════════════════ */}
        <div style={{
          flexShrink:0, zIndex:1, position:'relative',
          padding: collapsed ? '7px 5px' : '7px 10px',
          borderTop:`1px solid ${tk.footerBorder}`,
          display:'flex', flexDirection:'column', gap:'5px',
        }}>

          {/* User row */}
          {user && (
            <div
              title={collapsed ? `${user.full_name} · ${user.email}` : undefined}
              onClick={() => navigate('/app/settings')}
              style={{
                display:'flex', alignItems:'center',
                gap: collapsed ? 0 : '8px',
                padding: collapsed ? '6px 0' : '6px 8px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                borderRadius:'9px',
                background: tk.userRowBg,
                border:`1px solid ${tk.userRowBorder}`,
                cursor:'pointer', transition:'all 0.12s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background   = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(99,102,241,0.10)'
                e.currentTarget.style.borderColor  = isDark ? 'rgba(99,102,241,0.30)' : 'rgba(99,102,241,0.22)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background   = tk.userRowBg
                e.currentTarget.style.borderColor  = tk.userRowBorder
              }}
            >
              {/* Avatar */}
              <div style={{
                width:'28px', height:'28px', borderRadius:'8px', flexShrink:0,
                background:'linear-gradient(145deg,#6366f1,#a855f7)',
                display:'flex', alignItems:'center', justifyContent:'center',
                color:'#fff', fontWeight:800, fontSize:'10px',
                letterSpacing:'-0.02em',
                boxShadow:'0 3px 8px rgba(99,102,241,0.38)',
              }}>
                {initials}
              </div>

              {/* Name + email */}
              <div
                className="sb-fade"
                style={{
                  flex:1, minWidth:0, overflow:'hidden',
                  maxWidth: collapsed ? '0px' : '130px',
                  opacity:  collapsed ? 0 : 1,
                }}
              >
                <div style={{
                  fontSize:'12px', fontWeight:650,
                  color: tk.userName,
                  letterSpacing:'-0.02em',
                  whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
                }}>
                  {user.full_name}
                </div>
                <div style={{
                  fontSize:'10px', fontWeight:400,
                  color: tk.userEmail,
                  marginTop:'1px',
                  whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
                }}>
                  {user.email || 'Pro Member'}
                </div>
              </div>

              {!collapsed && (
                <ChevronRight
                  size={11} strokeWidth={2.5}
                  color={isDark ? 'rgba(255,255,255,0.28)' : '#9999b3'}
                  style={{ flexShrink:0 }}
                />
              )}
            </div>
          )}

          {/* ── COLLAPSE / EXPAND TOGGLE ── */}
          <button
            onClick={() => setCollapsed(c => !c)}
            className="sb-btn"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            style={{
              width:'100%', height:'30px', borderRadius:'8px',
              background: tk.toggleBg,
              border:`1px solid ${tk.toggleBorder}`,
              cursor:'pointer',
              display:'flex', alignItems:'center', justifyContent:'center', gap:'6px',
              color: tk.toggleColor,
            }}
          >
            {collapsed
              ? <PanelLeftOpen  size={13} strokeWidth={2}/>
              : <PanelLeftClose size={13} strokeWidth={2}/>
            }
            {!collapsed && (
              <span style={{
                fontSize:'11px', fontWeight:600,
                letterSpacing:'-0.01em',
                color: tk.toggleColor,
              }}>
                Collapse
              </span>
            )}
          </button>

          {/* Version */}
          {!collapsed && (
            <div style={{
              textAlign:'center', fontSize:'9px',
              color: tk.versionColor,
              fontFamily:'monospace', letterSpacing:'0.04em',
            }}>
              v4.0 · AI Meeting Intelligence
            </div>
          )}
        </div>
      </aside>
    </>
  )
}