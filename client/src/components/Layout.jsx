// components/Layout.jsx
// FIX: black area below content fixed with background on html/body level
// FIX: useScreenSize race condition handled by checking width directly

import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import BottomNav from './BottomNav'
import MobileTopBar, { MOBILE_TOPBAR_HEIGHT } from './MobileTopBar'
import FloatingChat from './FloatingChat'
import { useTheme } from '../ThemeContext'
import { useScreenSize } from '../hooks/useScreenSize'

const EW = 248   // expanded sidebar width
const CW = 54    // collapsed rail width

export default function Layout() {
  const { T }                              = useTheme()
  const { isMobile, isTablet, isDesktop }  = useScreenSize()
  const [collapsed, setCollapsed]          = useState(false)

  // Auto-collapse sidebar on tablet
  useEffect(() => {
    if (isTablet)  setCollapsed(true)
    if (isDesktop) setCollapsed(false)
  }, [isTablet, isDesktop])

  const sidebarW  = isMobile ? 0 : (collapsed ? CW : EW)
  const bottomPad = isMobile ? '80px' : '40px'

  // FIX: sync background to html element to prevent black flash/gap
  // Without this, areas below the content (when page is short) show
  // the browser's default white/black background instead of T.bg
  useEffect(() => {
    document.documentElement.style.background = T.bg
    document.body.style.background = T.bg
    document.body.style.margin = '0'
    document.body.style.minHeight = '100vh'
  }, [T.bg])

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: T.bg,
      transition: 'background 0.2s ease',
      fontFamily: 'var(--font)',
    }}>

      {/* Sidebar — hidden on mobile */}
      {!isMobile && (
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
      )}

      {/* Top bar — mobile only. Gives mobile a place for the workspace
          switcher, since the bottom bar is already full of nav icons. */}
      {isMobile && <MobileTopBar />}

      {/* Main content */}
      <main style={{
        marginLeft: `${sidebarW}px`,
        width: `calc(100% - ${sidebarW}px)`,
        flex: 1,
        minHeight: '100vh',
        background: T.bg,
        transition: 'margin-left 0.24s cubic-bezier(0.4,0,0.2,1), width 0.24s cubic-bezier(0.4,0,0.2,1)',
        display: 'flex',
        justifyContent: 'center',
      }}>

        {/* Content wrapper */}
        <div style={{
          width: '100%',
          maxWidth: '1200px',
          padding: isMobile
            ? `${MOBILE_TOPBAR_HEIGHT + 16}px 16px ${bottomPad}`
            : isTablet
              ? `32px 28px 40px`
              : '40px 40px',
          position: 'relative',
          boxSizing: 'border-box',
        }}>
          <Outlet />
        </div>
      </main>

      {/* Bottom nav — mobile only */}
      {isMobile && <BottomNav />}

      {/* Floating chat — desktop/tablet only */}
      {/* FIX: this used to be `{!isMobile && <FloatingChat />}` — hidden on
          mobile entirely, even though BottomNav's 5 quick icons don't
          include Chat, so mobile had no fast way to ask the AI anything.
          FloatingChat now handles its own responsive positioning/sizing
          internally, so it can render on every breakpoint. */}
      <FloatingChat />
    </div>
  )
}