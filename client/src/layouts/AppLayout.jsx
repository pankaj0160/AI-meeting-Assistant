// FILE: src/layouts/AppLayout.jsx
// Wires the sidebar collapsed/expanded state to the main content margin.
// Gives the dashboard area a visually distinct surface from the sidebar.

import { useState, createContext, useContext, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { useTheme } from '../ThemeContext'

// ─── sidebar state context ────────────────────────────────────────────────────
// Share collapsed state between Sidebar and AppLayout so the main content
// margin animates in sync with the sidebar width transition.
export const SidebarCtx = createContext({
  collapsed:   false,
  setCollapsed: () => {},
})
export const useSidebar = () => useContext(SidebarCtx)

// ─── constants ─────────────────────────────────────────────────────────────── 
const EXPANDED_W  = 240
const COLLAPSED_W = 56

export default function AppLayout() {
  const { isDark }               = useTheme()
  const [collapsed, setCollapsed] = useState(false)

  const sidebarW = collapsed ? COLLAPSED_W : EXPANDED_W

  // Dashboard surface — clearly different from sidebar
  // Sidebar: deep indigo-black / cool lavender-white
  // Dashboard: near-neutral dark / clean white with subtle warm tint
  const mainBg = isDark
    ? '#0a0912'         // slightly warmer black vs sidebar's blue-black
    : '#f7f6ff'         // very faint lavender — cooler than pure white

  return (
    <SidebarCtx.Provider value={{ collapsed, setCollapsed }}>

      {/* ── global layout style ── */}
      <style>{`
        .app-main {
          transition: margin-left 0.26s cubic-bezier(0.4,0,0.2,1),
                      background  0.22s ease;
        }
      `}</style>

      <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />

      <main
        className="app-main"
        style={{
          marginLeft: `${sidebarW}px`,
          minHeight:  '100vh',
          background: mainBg,

          /*
           * Visual separation from sidebar:
           * - different background tone
           * - inner left shadow creates depth/layering
           */
          boxShadow: isDark
            ? 'inset 2px 0 12px rgba(0,0,0,0.30)'
            : 'inset 2px 0 10px rgba(99,102,241,0.05)',

          /* ensure content never touches the left edge */
          padding: 0,
          position: 'relative',
        }}
      >
        {/* Optional subtle top-left gradient bleed from sidebar color */}
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0,
          height: '180px',
          background: isDark
            ? 'linear-gradient(180deg, rgba(99,102,241,0.035) 0%, transparent 100%)'
            : 'linear-gradient(180deg, rgba(99,102,241,0.025) 0%, transparent 100%)',
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