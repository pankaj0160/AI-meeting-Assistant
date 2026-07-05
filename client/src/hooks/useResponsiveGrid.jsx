// hooks/useResponsiveGrid.js
//
// Returns the right CSS grid-template-columns string for the current screen.
// Usage:
//   const grid = useResponsiveGrid()
//   <div style={{ display: 'grid', gridTemplateColumns: grid.cols4 }}>
//
// Instead of writing the same breakpoint logic in every page,
// all pages import this one hook. Change here = changes everywhere.

import { useScreenSize } from './useScreenSize'

export function useResponsiveGrid() {
  const { isMobile, isTablet } = useScreenSize()

  return {
    // 4-column on desktop, 2 on tablet, 1 on mobile
    cols4: isMobile ? '1fr 1fr' : isTablet ? '1fr 1fr' : 'repeat(4, 1fr)',
    // 3-column on desktop, 2 on tablet, 1 on mobile
    cols3: isMobile ? '1fr'     : isTablet ? '1fr 1fr' : 'repeat(3, 1fr)',
    // 2-column on desktop, 1 on mobile/tablet
    cols2: isMobile ? '1fr'     : isTablet ? '1fr'     : '1fr 1fr',
    // Always 1 column
    cols1: '1fr',
    // Gap — smaller on mobile
    gap:   isMobile ? '12px'    : '16px',
    // Padding inside cards
    pad:   isMobile ? '16px'    : '24px',
    isMobile,
    isTablet,
  }
}