// client/src/components/Layout.jsx

import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import FloatingChat from './FloatingChat'
import { useTheme } from '../ThemeContext'

/* ── Global keyframe + font injection (runs once) ── */
const injectGlobalStyles = () => {
  if (document.getElementById('summly-global-styles')) return
  const el = document.createElement('style')
  el.id = 'summly-global-styles'
  el.textContent = `
    @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,300;12..96,400;12..96,500;12..96,600;12..96,700;12..96,800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@300;400;500&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --font-display: 'Bricolage Grotesque', sans-serif;
      --font-body:    'DM Sans', sans-serif;
      --font-mono:    'DM Mono', monospace;
      --radius-sm:    8px;
      --radius-md:    12px;
      --radius-lg:    18px;
      --radius-xl:    24px;
      --ease-spring:  cubic-bezier(0.34, 1.56, 0.64, 1);
      --ease-smooth:  cubic-bezier(0.4, 0, 0.2, 1);
    }

    body {
      font-family: var(--font-body);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      font-feature-settings: 'ss01' 1, 'ss02' 1, 'cv01' 1;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(128,128,255,0.15); border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(128,128,255,0.28); }

    /* Skeleton shimmer */
    @keyframes skeleton-shimmer {
      0%   { background-position: -600px 0; }
      100% { background-position:  600px 0; }
    }
    .skeleton {
      background: linear-gradient(
        90deg,
        var(--skeleton-base) 0px,
        var(--skeleton-shine) 160px,
        var(--skeleton-base) 320px
      );
      background-size: 600px 100%;
      animation: skeleton-shimmer 1.6s infinite linear;
      border-radius: 6px;
    }

    /* Page enter animations */
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(18px); }
      to   { opacity: 1; transform: translateY(0);    }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    @keyframes scaleIn {
      from { opacity: 0; transform: scale(0.96); }
      to   { opacity: 1; transform: scale(1);    }
    }
    @keyframes slideRight {
      from { opacity: 0; transform: translateX(-14px); }
      to   { opacity: 1; transform: translateX(0);     }
    }
    @keyframes pulseGlow {
      0%, 100% { opacity: 0.5; transform: scale(1);    }
      50%       { opacity: 1;   transform: scale(1.15); }
    }
    @keyframes dotPulse {
      0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
      40%            { transform: scale(1);   opacity: 1;   }
    }
    @keyframes spinSlow {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }
    @keyframes borderGlow {
      0%, 100% { box-shadow: 0 0 0 0 var(--accent); }
      50%       { box-shadow: 0 0 14px 2px var(--accent); }
    }

    .anim-fade-in  { animation: fadeIn  0.35s var(--ease-smooth) both; }
    .anim-fade-up  { animation: fadeUp  0.45s var(--ease-smooth) both; }
    .anim-scale-in { animation: scaleIn 0.35s var(--ease-spring)  both; }
    .anim-slide-r  { animation: slideRight 0.38s var(--ease-smooth) both; }

    .anim-fade-up-1 { animation-delay: 0.06s; }
    .anim-fade-up-2 { animation-delay: 0.12s; }
    .anim-fade-up-3 { animation-delay: 0.18s; }
    .anim-fade-up-4 { animation-delay: 0.24s; }
    .anim-fade-up-5 { animation-delay: 0.30s; }

    /* Focus ring */
    :focus-visible {
      outline: 2px solid var(--accent);
      outline-offset: 2px;
      border-radius: 4px;
    }

    a { color: inherit; text-decoration: none; }
    button { font-family: inherit; }
    input, textarea, select { font-family: inherit; }
  `
  document.head.appendChild(el)
}

injectGlobalStyles()

export default function Layout() {
  const { T } = useTheme()

  return (
    <div style={{
      display: 'flex',
      minHeight: '100vh',
      background: T.bg,
      transition: 'background var(--transition)',
      fontFamily: 'var(--font-body)',
    }}>
      <Sidebar />

      <main style={{
        marginLeft: '305px',
        width: 'calc(100% - 305px)',
        flex: 1,
        padding: '40px 44px',
        minHeight: '100vh',
        background: T.bg,
        transition: 'background var(--transition)',
        position: 'relative',
      }}>
        {/* Subtle noise texture overlay */}
        <div style={{
          position: 'fixed',
          inset: 0,
          marginLeft: '305px',
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E")`,
          pointerEvents: 'none',
          zIndex: 0,
          opacity: 0.4,
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <Outlet />
        </div>
      </main>

      <FloatingChat />
    </div>
  )
}