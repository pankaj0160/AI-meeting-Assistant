// components/Logo.jsx
//
// Single source of truth for the Summly mark. Before this, the app had
// FOUR different inline logo implementations that had drifted out of sync:
//   - Navbar.jsx, BottomNav.jsx, MobileTopBar.jsx: an "S" lettermark in a
//     rounded chip (three separate copies of near-identical JSX)
//   - Login.jsx, Register.jsx, ForgotPassword.jsx: a completely different
//     mark — a mic icon in a gradient chip
// So the auth pages and the app pages didn't even share a logo. This
// component replaces all of them with one waveform mark: 5 vertical bars
// that read as an abstract "S" (Summly) while also being literally what
// the product processes — audio. The center bar (tallest) acts as the
// mark's "spine," and the smallest bar doubles as a signal/amber accent —
// a small brand moment rather than a decorative flourish.
//
// Usage:
//   <Logo />                          // full: chip + "Summly" wordmark
//   <Logo variant="icon" size={30} /> // chip only, no wordmark
//   <Logo variant="mono-white" />     // icon only, all-white, no chip —
//                                     // for use on colored/gradient surfaces
//   <Logo variant="bare" size={16} /> // just the SVG mark, no chip, no
//                                     // wordmark — for favicon/app-icon export

import { useTheme } from '../ThemeContext'

// Bar heights are relative units on a 34x34 viewBox, tallest = center "spine".
const BAR_HEIGHTS = [6, 14, 22, 10, 4]
const BAR_CENTERS = [5, 11, 17, 23, 29]
const BAR_WIDTH   = 4
const BASELINE    = 27

function WaveformMark({ size, accent, ink, signal }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 34 34"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {BAR_HEIGHTS.map((h, i) => {
        // Center bar = ink (the "spine" of the S). Last bar = signal/amber
        // accent (the smallest, brightest moment). The rest = brand accent.
        const fill = i === 2 ? ink : i === 4 ? signal : accent
        return (
          <rect
            key={i}
            x={BAR_CENTERS[i] - BAR_WIDTH / 2}
            y={BASELINE - h}
            width={BAR_WIDTH}
            height={h}
            rx={2}
            fill={fill}
          />
        )
      })}
    </svg>
  )
}

export default function Logo({ variant = 'full', size = 34, wordmarkSize, onClick }) {
  const { T, isDark } = useTheme()

  const isWhite    = variant === 'mono-white'
  const chipBg     = isWhite ? 'transparent' : (isDark ? '#1A1A1D' : '#EBEBEA')
  const chipBorder = isWhite ? 'transparent' : (isDark ? '#2A2A2E' : '#D8D8D4')
  const accent     = isWhite ? '#fff' : T.accent
  const ink        = isWhite ? '#fff' : T.text
  const signal     = isWhite ? '#fff' : T.amber

  const markSize = Math.round(size * 0.56)
  const mark = <WaveformMark size={markSize} accent={accent} ink={ink} signal={signal} />

  if (variant === 'bare') return mark

  // Render as a real <button> when clickable, not a div — a div with onClick
  // is invisible to keyboard navigation and screen readers. Unstyled to
  // look identical to the non-interactive chip below.
  const ChipTag = onClick ? 'button' : 'div'
  const chip = (
    <ChipTag
      onClick={onClick}
      aria-label={onClick ? 'Go to dashboard' : undefined}
      style={{
        width: size, height: size, borderRadius: Math.round(size * 0.27),
        background: chipBg,
        border: isWhite ? 'none' : `1px solid ${chipBorder}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        cursor: onClick ? 'pointer' : 'default',
        padding: 0,
        font: 'inherit',
        appearance: 'none',
        WebkitAppearance: 'none',
      }}
    >
      {mark}
    </ChipTag>
  )

  if (variant === 'icon' || variant === 'mono-white') return chip

  // variant === 'full' — chip + wordmark, side by side
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
      {chip}
      <span style={{
        fontSize: wordmarkSize || Math.round(size * 0.53),
        fontWeight: 800, letterSpacing: '-0.05em',
        color: isWhite ? '#fff' : T.text,
      }}>
        Summly
      </span>
    </div>
  )
}