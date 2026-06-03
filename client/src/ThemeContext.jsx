import { createContext, useContext, useState } from 'react'
import { DARK, LIGHT } from './theme'

const Ctx = createContext(null)

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(true)
  const T = isDark ? DARK : LIGHT

  // Inject skeleton CSS vars into :root dynamically
  const style = document.documentElement.style
  style.setProperty('--skeleton-base', T.skeletonBase)
  style.setProperty('--skeleton-shine', T.skeletonShine)

  return (
    <Ctx.Provider value={{ T, isDark, toggle: () => setIsDark(d => !d) }}>
      {children}
    </Ctx.Provider>
  )
}

export const useTheme = () => useContext(Ctx)