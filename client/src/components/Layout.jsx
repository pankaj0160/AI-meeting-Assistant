// client/src/components/Layout.jsx

import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import FloatingChat from './FloatingChat'
import { useTheme } from '../ThemeContext'

export default function Layout() {
  const { T } = useTheme()

  return (
    <div style={{
      display: 'flex', minHeight: '100vh',
      background: T.bg,
      transition: `background var(--transition)`,
    }}>
      <Sidebar />
      <main style={{
        marginLeft: '228px',
        flex: 1,
        padding: '36px 40px',
        minHeight: '100vh',
        background: T.bg,
        transition: `background var(--transition)`,
      }}>
        <Outlet />
      </main>
       <FloatingChat />
    </div>
  )
}