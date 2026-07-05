// hooks/useScreenSize.js
//
// WHAT CHANGED AND WHY:
// ──────────────────────
// The old version computed breakpoints from `window.innerWidth`, read once
// on mount and then re-read on a 50ms-debounced 'resize' listener. That's
// fragile in a few real ways:
//   - `window.innerWidth` reflects the *layout* viewport, which can differ
//     from the visual viewport a device is actually rendering at (e.g. iOS
//     Safari's dynamic toolbar, some Android WebViews, or any page that
//     briefly renders before viewport/zoom settles) — a desktop sidebar
//     showing up on an actual phone is the classic symptom of this class
//     of bug.
//   - Every consumer got its own copy of "mobile / tablet / desktop", each
//     one only as correct as that last debounced resize event.
//
// `window.matchMedia` is the browser's own authoritative breakpoint engine:
// it's what CSS media queries use internally, it's correct from the very
// first render (no waiting for a resize event to fire), and it fires a
// native 'change' event the instant the viewport actually crosses a
// breakpoint — no debounce/race window at all.

import { useState, useEffect } from 'react'

const MOBILE_BP = 768   // < 768        → mobile
const TABLET_BP = 1024  // 768–1023     → tablet
                        // >= 1024      → desktop

function query(bp, dir) {
  // dir: 'max' → matches below bp, 'min' → matches at/above bp
  return typeof window !== 'undefined'
    ? window.matchMedia(dir === 'max' ? `(max-width: ${bp - 1}px)` : `(min-width: ${bp}px)`)
    : null
}

function getCategory() {
  if (typeof window === 'undefined') return 'desktop'
  if (query(MOBILE_BP, 'max')?.matches) return 'mobile'
  if (query(TABLET_BP, 'max')?.matches) return 'tablet'
  return 'desktop'
}

export function useScreenSize() {
  const [category, setCategory] = useState(getCategory)

  useEffect(() => {
    const mobileQuery = query(MOBILE_BP, 'max')
    const tabletQuery = query(TABLET_BP, 'max')
    if (!mobileQuery || !tabletQuery) return

    const update = () => setCategory(getCategory())
    update() // re-sync immediately on mount, in case anything changed pre-hydration

    // addEventListener('change', ...) is the modern API; addListener is the
    // deprecated fallback still needed on some older WebViews.
    const subscribe = (mql, fn) => {
      if (mql.addEventListener) mql.addEventListener('change', fn)
      else mql.addListener(fn)
      return () => {
        if (mql.removeEventListener) mql.removeEventListener('change', fn)
        else mql.removeListener(fn)
      }
    }

    const unsub1 = subscribe(mobileQuery, update)
    const unsub2 = subscribe(tabletQuery, update)
    return () => { unsub1(); unsub2() }
  }, [])

  return {
    isMobile:  category === 'mobile',
    isTablet:  category === 'tablet',
    isDesktop: category === 'desktop',
    category,
  }
}