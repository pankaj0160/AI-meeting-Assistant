// FILE: src/layouts/AppLayout.jsx
// Wires the sidebar collapsed/expanded state to the main content margin.
// Gives the dashboard area a visually distinct surface from the sidebar.
// FIX: mobile — sidebar overlays at ≤768px, margin-left zeroed out.

import { useState, createContext, useContext, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useTheme } from '../ThemeContext'
import { useScreenSize } from '../hooks/useScreenSize'

// ─── sidebar state context ────────────────────────────────────────────────────
export const SidebarCtx = createContext({
  collapsed:    false,
  setCollapsed: () => {},
  isMobile:     false,
})
export const useSidebar = () => useContext(SidebarCtx)

// ─── constants ────────────────────────────────────────────────────────────────
const EXPANDED_W  = 240
const COLLAPSED_W = 56
const MOBILE_BP   = 768

export default function AppLayout() {
  const { isDark } = useTheme()

  const [collapsed,  setCollapsed]  = useState(false)
  // FIX: was its own window.innerWidth + resize-listener implementation —
  // exactly the fragile pattern useScreenSize.jsx's own comments describe
  // replacing app-wide (stale on first paint, no correctness guarantee
  // against the visual viewport). This is the code deciding whether the
  // sidebar overlays or pushes content, so it's worth using the same
  // authoritative source of truth as every other responsive decision.
  const { isMobile } = useScreenSize()
  const [sidebarOpen, setSidebarOpen] = useState(false) // mobile overlay open state

  // Close the mobile overlay if the viewport crosses back to desktop
  // (e.g. rotating a tablet, or a phone's split-screen mode resizing).
  useEffect(() => {
    if (!isMobile) setSidebarOpen(false)
  }, [isMobile])

  // On mobile the sidebar is an overlay (0 margin), on desktop it pushes content
  const sidebarW = isMobile ? 0 : (collapsed ? COLLAPSED_W : EXPANDED_W)

  // FIX: was '#0a0912' / '#f7f6ff' — literally documented in the old comment
  // as "blue-black" / "faint lavender", a violet tint that had crept in here
  // too. Neutral near-black / near-white now, consistent with the emerald
  // brand having no blue-violet in it anywhere.
  const mainBg = isDark
    ? '#0A0B0A'
    : '#F7F8F7'

  return (
    <SidebarCtx.Provider value={{ collapsed, setCollapsed, isMobile, sidebarOpen, setSidebarOpen }}>

      <style>{`
        .app-main {
          transition: margin-left 0.26s cubic-bezier(0.4, 0, 0.2, 1),
                      background  0.22s ease;
        }

        /* Mobile overlay backdrop */
        .sidebar-backdrop {
          display: none;
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.55);
          z-index: 99;
          backdrop-filter: blur(2px);
          -webkit-backdrop-filter: blur(2px);
        }
        .sidebar-backdrop.visible {
          display: block;
        }

        @media (max-width: ${MOBILE_BP}px) {
          .app-main {
            margin-left: 0 !important;
            /* Extra bottom padding for mobile so content clears nav */
            padding-bottom: 24px;
          }
        }
      `}</style>

      {/* Mobile backdrop — tapping it closes the sidebar */}
      {isMobile && sidebarOpen && (
        <div
          className="sidebar-backdrop visible"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <Sidebar
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        isMobile={isMobile}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
      />

      <main
        className="app-main"
        style={{
          marginLeft: `${sidebarW}px`,
          minHeight:  '100vh',
          background: mainBg,
          boxShadow: isDark
            ? 'inset 2px 0 12px rgba(0,0,0,0.30)'
            : 'inset 2px 0 10px rgba(5,150,105,0.04)',
          padding:  0,
          position: 'relative',
          // Prevent content from being hidden under a fixed/absolute sidebar on mobile
          overflowX: 'hidden',
        }}
      >
        {/* Subtle top gradient bleed from sidebar color */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0,
          height: '180px',
          background: isDark
            ? 'linear-gradient(180deg, rgba(16,185,129,0.03) 0%, transparent 100%)'
            : 'linear-gradient(180deg, rgba(5,150,105,0.02) 0%, transparent 100%)',
          pointerEvents: 'none',
          zIndex: 0,
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <Outlet />
        </div>
      </main>

    </SidebarCtx.Provider>
  )
}