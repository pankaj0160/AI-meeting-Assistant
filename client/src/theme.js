// client/src/theme.js

export const DARK = {
  // ── Backgrounds
  bg:           '#080b12',
  bgSubtle:     '#060810',
  surface:      '#0d1120',
  surface2:     '#111827',
  surface3:     '#151d2e',
  surfaceHover: '#192035',

  // ── Borders
  border:       '#1c2540',
  border2:      '#253050',
  borderFocus:  '#6366f1',

  // ── Text — maximum readability on dark
  text:         '#f0f4ff',
  text2:        '#c4cde8',
  text3:        '#6b7799',
  text4:        '#384060',

  // ── Brand accent (indigo/violet)
  accent:       '#6366f1',
  accentLight:  '#818cf8',
  accentBg:     'rgba(99,102,241,0.13)',
  accentHover:  'rgba(99,102,241,0.20)',

  // ── Semantic colors
  blue:         '#3b82f6',
  blueBg:       'rgba(59,130,246,0.12)',
  blueText:     '#93c5fd',

  purple:       '#a855f7',
  purpleBg:     'rgba(168,85,247,0.12)',
  purpleText:   '#d8b4fe',

  orange:       '#f97316',
  orangeBg:     'rgba(249,115,22,0.12)',
  orangeText:   '#fed7aa',

  emerald:      '#10b981',
  emeraldBg:    'rgba(16,185,129,0.12)',
  emeraldText:  '#6ee7b7',

  cyan:         '#06b6d4',
  cyanBg:       'rgba(6,182,212,0.12)',
  cyanText:     '#67e8f9',

  rose:         '#f43f5e',
  roseBg:       'rgba(244,63,94,0.12)',
  roseText:     '#fda4af',

  success:      '#10b981',
  successBg:    'rgba(16,185,129,0.12)',
  warning:      '#f59e0b',
  warningBg:    'rgba(245,158,11,0.12)',
  danger:       '#ef4444',
  dangerBg:     'rgba(239,68,68,0.12)',

  // ── UI
  btnGrad:      'linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #06b6d4 100%)',
  btnShadow:    '0 4px 24px rgba(99,102,241,0.45)',
  cardShadow:   '0 1px 2px rgba(0,0,0,0.6), 0 8px 32px rgba(0,0,0,0.35)',
  cardShadowHover: '0 6px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.15)',

  // ── Sidebar
  sidebarBg:    '#060810',
  sidebarBorder:'#141928',
  navColor:     '#4a5270',
  navHover:     '#8892b0',
  navActiveText:'#f0f4ff',
  navActiveBg:  'rgba(99,102,241,0.16)',
  navActiveBorder: 'rgba(99,102,241,0.35)',

  // ── Inputs
  inputBg:      '#0d1120',
  inputBorder:  '#1c2540',

  // ── Skeleton
  skeletonBase: '#111827',
  skeletonShine:'#1a2235',

  // ── Toggle
  toggleBg:     '#111827',
  toggleBorder: '#1c2540',
  toggleColor:  '#6b7799',

  // ── Glow effects
  glowAccent:   'rgba(99,102,241,0.35)',
  glowPurple:   'rgba(168,85,247,0.25)',
  glowCyan:     'rgba(6,182,212,0.20)',
}

export const LIGHT = {
  // ── Backgrounds — warm ivory/cream base
  bg:           '#f5f4f0',
  bgSubtle:     '#eeece7',
  surface:      '#ffffff',
  surface2:     '#faf9f6',
  surface3:     '#f0eeea',
  surfaceHover: '#fefefe',

  // ── Borders
  border:       '#e0ddd5',
  border2:      '#d0ccc2',
  borderFocus:  '#5046e4',

  // ── Text
  text:         '#0f0e0a',
  text2:        '#2c2a22',
  text3:        '#6b6556',
  text4:        '#a09880',

  // ── Brand accent
  accent:       '#5046e4',
  accentLight:  '#6366f1',
  accentBg:     'rgba(80,70,228,0.08)',
  accentHover:  'rgba(80,70,228,0.14)',

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
  btnGrad:      'linear-gradient(135deg, #5046e4 0%, #7c3aed 50%, #0891b2 100%)',
  btnShadow:    '0 4px 16px rgba(80,70,228,0.30)',
  cardShadow:   '0 1px 3px rgba(0,0,0,0.07), 0 6px 20px rgba(0,0,0,0.06)',
  cardShadowHover: '0 8px 32px rgba(0,0,0,0.12), 0 0 0 1px rgba(80,70,228,0.12)',

  // ── Sidebar
  sidebarBg:    '#eeece7',
  sidebarBorder:'#dddad0',
  navColor:     '#5a5545',
  navHover:     '#0f0e0a',
  navActiveText:'#0f0e0a',
  navActiveBg:  'rgba(80,70,228,0.10)',
  navActiveBorder:'rgba(80,70,228,0.25)',

  // ── Inputs
  inputBg:      '#ffffff',
  inputBorder:  '#e0ddd5',

  // ── Skeleton
  skeletonBase: '#e8e6e0',
  skeletonShine:'#f5f4f0',

  // ── Toggle
  toggleBg:     '#f0eeea',
  toggleBorder: '#e0ddd5',
  toggleColor:  '#6b6556',

  // ── Glow
  glowAccent:   'rgba(80,70,228,0.18)',
  glowPurple:   'rgba(124,58,237,0.12)',
  glowCyan:     'rgba(8,145,178,0.10)',
}