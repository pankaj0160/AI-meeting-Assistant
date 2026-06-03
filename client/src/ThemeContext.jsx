// client/src/ThemeContext.jsx

import { createContext, useContext, useState, useEffect } from 'react'
import { DARK, LIGHT } from './theme'

const Ctx = createContext(null)

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(() => {
    try {
      const saved = localStorage.getItem('summly-theme')
      return saved !== null ? saved === 'dark' : true
    } catch {
      return true
    }
  })

  const T = isDark ? DARK : LIGHT

  useEffect(() => {
    const root = document.documentElement
    const style = root.style

    // CSS vars for skeleton + transitions
    style.setProperty('--skeleton-base',  T.skeletonBase)
    style.setProperty('--skeleton-shine', T.skeletonShine)
    style.setProperty('--transition',     '0.22s ease')
    style.setProperty('--accent',         T.accent)
    style.setProperty('--bg',             T.bg)
    style.setProperty('--text',           T.text)

    // Body background
    document.body.style.background  = T.bg
    document.body.style.color       = T.text
    document.body.style.transition  = 'background 0.22s ease, color 0.22s ease'

    // Persist
    try { localStorage.setItem('summly-theme', isDark ? 'dark' : 'light') } catch {}
  }, [isDark, T])

  return (
    <Ctx.Provider value={{ T, isDark, toggle: () => setIsDark(d => !d) }}>
      {children}
    </Ctx.Provider>
  )
}

export const useTheme = () => useContext(Ctx)