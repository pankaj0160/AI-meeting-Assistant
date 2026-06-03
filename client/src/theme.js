// client/src/theme.js

export const DARK = {
  // ── Backgrounds
  bg:           '#13161e',
  bgSubtle:     '#0f1117',
  surface:      '#1a1e2a',
  surface2:     '#1f2436',
  surface3:     '#252b3b',
  surfaceHover: '#252d40',

  // ── Borders
  border:       '#272d3d',
  border2:      '#2f3650',
  borderFocus:  '#5b6af0',

  // ── Text — maximum readability on dark
  text:         '#eef0f6',
  text2:        '#aeb5cc',
  text3:        '#6b748f',
  text4:        '#3f4660',

  // ── Brand accent (indigo)
  accent:       '#5b6af0',
  accentLight:  '#7b8cf8',
  accentBg:     'rgba(91,106,240,0.12)',
  accentHover:  'rgba(91,106,240,0.18)',

  // ── Semantic colors
  // Summary → blue
  blue:         '#3b82f6',
  blueBg:       'rgba(59,130,246,0.10)',
  blueText:     '#93c5fd',

  // Decisions → purple
  purple:       '#a855f7',
  purpleBg:     'rgba(168,85,247,0.10)',
  purpleText:   '#d8b4fe',

  // Action items → orange
  orange:       '#f97316',
  orangeBg:     'rgba(249,115,22,0.10)',
  orangeText:   '#fdba74',

  // Tasks → emerald
  emerald:      '#10b981',
  emeraldBg:    'rgba(16,185,129,0.10)',
  emeraldText:  '#6ee7b7',

  // Speakers → cyan
  cyan:         '#06b6d4',
  cyanBg:       'rgba(6,182,212,0.10)',
  cyanText:     '#67e8f9',

  // Success / warning / danger
  success:      '#10b981',
  successBg:    'rgba(16,185,129,0.10)',
  warning:      '#f59e0b',
  warningBg:    'rgba(245,158,11,0.10)',
  danger:       '#ef4444',
  dangerBg:     'rgba(239,68,68,0.10)',

  // ── UI
  btnGrad:      'linear-gradient(135deg, #5b6af0, #a855f7)',
  btnShadow:    '0 4px 16px rgba(91,106,240,0.35)',
  cardShadow:   '0 1px 3px rgba(0,0,0,0.4), 0 6px 20px rgba(0,0,0,0.25)',
  cardShadowHover: '0 4px 24px rgba(0,0,0,0.4)',

  // ── Sidebar
  sidebarBg:    '#0f1117',
  sidebarBorder:'#1e2230',
  navColor:     '#5a6380',
  navHover:     '#9aa3be',
  navActiveText:'#eef0f6',
  navActiveBg:  'rgba(91,106,240,0.14)',
  navActiveBorder: 'rgba(91,106,240,0.30)',

  // ── Inputs
  inputBg:      '#1a1e2a',
  inputBorder:  '#272d3d',

  // ── Skeleton
  skeletonBase: '#1f2436',
  skeletonShine:'#252b3b',

  // ── Toggle
  toggleBg:     '#1f2436',
  toggleBorder: '#2f3650',
  toggleColor:  '#6b748f',
}

export const LIGHT = {
  // ── Backgrounds
  bg:           '#e8edf4',
  bgSubtle:     '#dde3ec',
  surface:      '#ffffff',
  surface2:     '#f2f5fb',
  surface3:     '#eaeff7',
  surfaceHover: '#f7f9fd',

  // ── Borders
  border:       '#d4daea',
  border2:      '#c5cedf',
  borderFocus:  '#4f46e5',

  // ── Text — maximum readability on light
  text:         '#0e1118',
  text2:        '#2e3650',
  text3:        '#5a6580',
  text4:        '#9aa3bc',

  // ── Brand accent
  accent:       '#4f46e5',
  accentLight:  '#6366f1',
  accentBg:     'rgba(79,70,229,0.07)',
  accentHover:  'rgba(79,70,229,0.12)',

  // ── Semantic
  blue:         '#2563eb',
  blueBg:       'rgba(37,99,235,0.07)',
  blueText:     '#1d4ed8',

  purple:       '#7c3aed',
  purpleBg:     'rgba(124,58,237,0.07)',
  purpleText:   '#5b21b6',

  orange:       '#ea580c',
  orangeBg:     'rgba(234,88,12,0.07)',
  orangeText:   '#9a3412',

  emerald:      '#059669',
  emeraldBg:    'rgba(5,150,105,0.07)',
  emeraldText:  '#065f46',

  cyan:         '#0891b2',
  cyanBg:       'rgba(8,145,178,0.07)',
  cyanText:     '#164e63',

  success:      '#059669',
  successBg:    'rgba(5,150,105,0.07)',
  warning:      '#d97706',
  warningBg:    'rgba(217,119,6,0.07)',
  danger:       '#dc2626',
  dangerBg:     'rgba(220,38,38,0.07)',

  // ── UI
  btnGrad:      'linear-gradient(135deg, #4f46e5, #7c3aed)',
  btnShadow:    '0 4px 14px rgba(79,70,229,0.28)',
  cardShadow:   '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.05)',
  cardShadowHover: '0 4px 24px rgba(0,0,0,0.10)',

  // ── Sidebar
  sidebarBg:    '#dde3ec',
  sidebarBorder:'#c8d0e0',
  navColor:     '#5a6580',
  navHover:     '#0e1118',
  navActiveText:'#0e1118',
  navActiveBg:  'rgba(79,70,229,0.10)',
  navActiveBorder:'rgba(79,70,229,0.22)',

  // ── Inputs
  inputBg:      '#ffffff',
  inputBorder:  '#d4daea',

  // ── Skeleton
  skeletonBase: '#e2e8f0',
  skeletonShine:'#f1f5f9',

  // ── Toggle
  toggleBg:     '#eaeff7',
  toggleBorder: '#d4daea',
  toggleColor:  '#5a6580',
}