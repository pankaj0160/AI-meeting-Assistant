// client/src/components/MobileTopBar.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// A slim, fixed top bar shown ONLY on mobile (<768px). Before this file
// existed, mobile had zero workspace-switching capability — BottomNav's
// 5-icon strip is already full, and its hamburger drawer was just a plain
// list of page links with no concept of "active workspace" anywhere.
//
// This bar sits above the page content and holds:
//   - the Summly mark (tap → dashboard)
//   - the workspace switcher chip (tap → same dropdown used everywhere else)
//   - a live/offline status dot
//
// It's intentionally minimal — 52px tall — so it doesn't eat into content
// space on small screens; Layout.jsx adds matching top padding.

import { useNavigate } from 'react-router-dom'
import { useTheme } from '../ThemeContext'
import WorkspaceSwitcher from './WorkspaceSwitcher'
import Logo from './Logo'

export const MOBILE_TOPBAR_HEIGHT = 52

export default function MobileTopBar() {
  const { T, isDark } = useTheme()
  const navigate = useNavigate()

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0,
      height: `${MOBILE_TOPBAR_HEIGHT}px`,
      zIndex: 199,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: '10px',
      padding: '0 14px',
      paddingTop: 'env(safe-area-inset-top)',
      background: isDark ? 'rgba(10,10,11,0.92)' : 'rgba(255,255,255,0.92)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      borderBottom: `1px solid ${T.border}`,
    }}>
      {/* Logo mark — tap → dashboard. Wrapped in a padded button rather than
          relying on the 30px chip itself as the tap target: the bar is only
          52px tall, so a visually-44px mark would look heavy, but the
          *tappable* area still needs to hit the 44px minimum. Padding gets
          us both. */}
      <button
        onClick={() => navigate('/app')}
        aria-label="Go to dashboard"
        style={{
          width: 44, height: 44, padding: 0,
          background: 'none', border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Logo variant="icon" size={30} />
      </button>

      {/* Workspace switcher — the whole reason this bar exists */}
      <div style={{ flex: 1, display: 'flex', justifyContent: 'center', minWidth: 0 }}>
        <WorkspaceSwitcher variant="chip" isDark={isDark} align="left" />
      </div>

      {/* Spacer to visually balance the logo mark so the chip stays centered */}
      <div style={{ width: 44, flexShrink: 0 }} />
    </div>
  )
}