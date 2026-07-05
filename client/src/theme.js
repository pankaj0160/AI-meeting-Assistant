// client/src/theme.js
// Brand v2 — clean dark slate + emerald accent
//
// Design direction:
//   Before: indigo/violet/cyan gradient everywhere = generic AI startup look
//   After:  near-black surface + single emerald accent = focused, confident tool
//
// Rules:
//   - One accent color (emerald #10b981) — not six
//   - No rainbow gradients on interactive elements
//   - Buttons are solid, not gradient
//   - Nav items are monochrome — only active uses accent
//   - Semantic colors (blue, orange, purple) still used for data viz / badges

export const DARK = {
  // ── Backgrounds — near-black with slight warmth (not pure #000)
  bg:           '#0A0A0B',
  bgSubtle:     '#080808',
  surface:      '#111113',
  surface2:     '#18181B',
  surface3:     '#1C1C1F',
  surfaceHover: '#202023',

  // ── Borders — subtle, not distracting
  border:       '#27272A',
  border2:      '#3F3F46',
  borderFocus:  '#10b981',

  // ── Text — warm white, not blue-white
  text:         '#FAFAFA',
  text2:        '#D4D4D8',
  // FIX (accessibility audit): text3 was 3.9:1 against surface — fails
  // normal-text WCAG AA (needs 4.5:1), and text3 is used for real small
  // text (captions, timestamps, secondary labels) sitewide, not large text.
  // text4 was 1.8:1 — failed even the large-text minimum (3:1). Both bumped;
  // text4 still reads visibly quieter than text3 but is no longer
  // functionally invisible for anyone with reduced contrast sensitivity.
  text3:        '#7C7C7C',
  text4:        '#616161',

  // ── Brand accent — emerald (single accent, used consistently)
  // Why emerald: unique among AI tools, associated with growth/intelligence,
  // works beautifully on dark backgrounds, not overused
  accent:       '#10b981',
  accentLight:  '#34d399',
  accentBg:     'rgba(16,185,129,0.10)',
  accentHover:  'rgba(16,185,129,0.18)',

  // ── Secondary accent — amber. Used sparingly: the logo's "signal" bar,
  // action-item highlights, warnings-lite. Never used for primary actions —
  // emerald stays the one accent on buttons/links/nav, per the brand rule above.
  amber:        '#F0B558',
  amberBg:      'rgba(240,181,88,0.12)',
  amberText:    '#F0B558',

  // ── Semantic colors — for data, badges, status indicators
  // These do NOT appear on interactive elements (buttons, nav)
  blue:         '#3b82f6',
  blueBg:       'rgba(59,130,246,0.10)',
  blueText:     '#93c5fd',

  purple:       '#a855f7',
  purpleBg:     'rgba(168,85,247,0.10)',
  purpleText:   '#d8b4fe',

  orange:       '#f97316',
  orangeBg:     'rgba(249,115,22,0.10)',
  orangeText:   '#fed7aa',

  emerald:      '#10b981',
  emeraldBg:    'rgba(16,185,129,0.10)',
  emeraldText:  '#6ee7b7',

  cyan:         '#06b6d4',
  cyanBg:       'rgba(6,182,212,0.10)',
  cyanText:     '#67e8f9',

  rose:         '#f43f5e',
  roseBg:       'rgba(244,63,94,0.10)',
  roseText:     '#fda4af',

  success:      '#10b981',
  successBg:    'rgba(16,185,129,0.10)',
  warning:      '#f59e0b',
  warningBg:    'rgba(245,158,11,0.10)',
  danger:       '#ef4444',
  dangerBg:     'rgba(239,68,68,0.10)',

  // ── UI elements
  // Buttons: solid dark with accent text/border — not gradient
  btnGrad:      '#111113',
  btnShadow:    '0 1px 2px rgba(0,0,0,0.5)',
  cardShadow:   '0 1px 3px rgba(0,0,0,0.4)',

  // ── Sidebar
  sidebarBg:    '#0A0A0B',
  sidebarBorder:'#1A1A1D',
  navColor:     '#52525B',
  navHover:     '#A1A1AA',
  navActiveText:'#FAFAFA',
  navActiveBg:  'rgba(16,185,129,0.10)',
  navActiveBorder: 'rgba(16,185,129,0.25)',

  // ── Inputs
  inputBg:      '#111113',
  inputBorder:  '#27272A',

  // ── Skeleton shimmer
  skeletonBase: '#18181B',
  skeletonShine:'#27272A',

  // ── Toggle
  toggleBg:     '#18181B',
  toggleBorder: '#27272A',
  toggleColor:  '#71717A',

  // ── Glow — emerald only
  glowAccent:   'rgba(16,185,129,0.20)',
  glowPurple:   'rgba(168,85,247,0.12)',
  glowCyan:     'rgba(6,182,212,0.10)',
}

export const LIGHT = {
  // ── Backgrounds — warm ivory base (not cold grey)
  bg:           '#F8F8F7',
  bgSubtle:     '#F0F0EE',
  surface:      '#FFFFFF',
  surface2:     '#F4F4F3',
  surface3:     '#EBEBEA',
  surfaceHover: '#FEFEFE',

  // ── Borders
  border:       '#E4E4E2',
  border2:      '#D4D4D0',
  borderFocus:  '#059669',

  // ── Text — warm black
  text:         '#111110',
  text2:        '#3A3A38',
  // FIX (accessibility audit): same contrast issue as dark theme — see
  // comment there. text3 was 3.5:1, text4 was 1.9:1, both failed AA.
  text3:        '#727272',
  text4:        '#909090',

  // ── Brand accent — darker emerald on light
  accent:       '#059669',
  accentLight:  '#10b981',
  accentBg:     'rgba(5,150,105,0.08)',
  accentHover:  'rgba(5,150,105,0.14)',

  // ── Secondary accent — amber (darker for light-background contrast)
  amber:        '#B8791E',
  amberBg:      'rgba(184,121,30,0.10)',
  amberText:    '#8A5A15',

  // ── Semantic
  blue:         '#2563eb',
  blueBg:       'rgba(37,99,235,0.08)',
  blueText:     '#1d4ed8',

  purple:       '#7c3aed',
  purpleBg:     'rgba(124,58,237,0.08)',
  purpleText:   '#6d28d9',

  orange:       '#ea580c',
  orangeBg:     'rgba(234,88,12,0.08)',
  orangeText:   '#c2410c',

  emerald:      '#059669',
  emeraldBg:    'rgba(5,150,105,0.08)',
  emeraldText:  '#047857',

  cyan:         '#0891b2',
  cyanBg:       'rgba(8,145,178,0.08)',
  cyanText:     '#0e7490',

  rose:         '#e11d48',
  roseBg:       'rgba(225,29,72,0.08)',
  roseText:     '#be185d',

  success:      '#059669',
  successBg:    'rgba(5,150,105,0.08)',
  warning:      '#d97706',
  warningBg:    'rgba(217,119,6,0.08)',
  danger:       '#dc2626',
  dangerBg:     'rgba(220,38,38,0.08)',

  // ── UI
  btnGrad:      '#111110',
  btnShadow:    '0 1px 2px rgba(0,0,0,0.12)',
  cardShadow:   '0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)',

  // ── Sidebar
  sidebarBg:    '#F0F0EE',
  sidebarBorder:'#E0E0DC',
  navColor:     '#8A8A85',
  navHover:     '#111110',
  navActiveText:'#111110',
  navActiveBg:  'rgba(5,150,105,0.08)',
  navActiveBorder:'rgba(5,150,105,0.20)',

  // ── Inputs
  inputBg:      '#FFFFFF',
  inputBorder:  '#E4E4E2',

  // ── Skeleton
  skeletonBase: '#E8E8E5',
  skeletonShine:'#F4F4F3',

  // ── Toggle
  toggleBg:     '#F0F0EE',
  toggleBorder: '#E4E4E2',
  toggleColor:  '#8A8A85',

  // ── Glow
  glowAccent:   'rgba(5,150,105,0.12)',
  glowPurple:   'rgba(124,58,237,0.08)',
  glowCyan:     'rgba(8,145,178,0.08)',
}