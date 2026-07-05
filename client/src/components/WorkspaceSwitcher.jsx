// client/src/components/WorkspaceSwitcher.jsx
//
// WHAT THIS FILE DOES:
// ────────────────────
// One workspace switcher, used in three places:
//   - Sidebar, expanded          → variant="bar"  (full pill: dot + name + chevron)
//   - Sidebar, collapsed to rail → variant="icon" (just a colored dot button)
//   - Mobile top bar             → variant="chip" (compact dot + short name)
//
// WHY THIS EXISTS:
// ─────────────────
// The old implementation lived inside the Sidebar's collapsible nav block,
// which gets `maxHeight: 0`'d away whenever the sidebar collapses — and the
// sidebar auto-collapses on tablets. Net effect: on any tablet, and on
// desktop whenever the user collapsed the sidebar, the workspace switcher
// (and the "which workspace am I looking at" concept) simply vanished with
// no icon, no indicator, nothing. Mobile never had one at all.
//
// This version fixes that at the root: the switcher is a self-contained
// component that always renders something clickable, however little space
// it's given (down to a single 28px dot), and its dropdown is rendered via
// a portal straight into document.body — positioned from the trigger's own
// bounding box — so it always escapes narrow containers instead of being
// clipped by a parent's `overflow: hidden` (which is what silently broke
// the old dropdown-inside-a-54px-rail case).

import { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, Check, Layers } from 'lucide-react'
import { useWorkspace } from '../context/WorkspaceContext'
import { useTheme } from '../ThemeContext'

export default function WorkspaceSwitcher({
  variant = 'bar',      // 'bar' | 'icon' | 'chip'
  isDark  = false,
  align   = 'left',     // which side the dropdown hangs from, for 'bar'/'chip'
}) {
  const { workspaces, activeWorkspaceId, activeWorkspace, selectWorkspace } = useWorkspace() || {}
  const { T } = useTheme()
  const [open, setOpen]   = useState(false)
  const [rect, setRect]   = useState(null)
  const triggerRef        = useRef(null)
  const navigate          = useNavigate()

  const color = activeWorkspace?.color || (isDark ? 'rgba(255,255,255,0.35)' : T.text3)

  // Recompute the trigger's position right before paint whenever it opens,
  // and keep it in sync on scroll/resize while open (e.g. collapsing the
  // sidebar while the flyout is open, or rotating a phone).
  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return
    const update = () => setRect(triggerRef.current.getBoundingClientRect())
    update()
    window.addEventListener('resize', update)
    window.addEventListener('scroll', update, true)
    return () => {
      window.removeEventListener('resize', update)
      window.removeEventListener('scroll', update, true)
    }
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  function pick(id) {
    selectWorkspace?.(id)
    setOpen(false)
  }

  // ── Theming ──────────────────────────────────────────────────────────────
  // Was hardcoded indigo throughout (panel border, hover tint, "Manage
  // Workspaces" text) — now derives from the shared emerald accent tokens.
  const panelBg     = T.surface2
  const panelBorder = T.border2
  const itemHoverBg = isDark ? 'rgba(255,255,255,0.06)' : T.accentBg
  const itemText    = T.text
  const mutedText   = T.text3
  const accentColor = T.accent

  // ── Dropdown panel, portalled to <body> and positioned from `rect` ──────
  function Panel() {
    if (!rect) return null

    // For icon variant (collapsed rail): open to the right of the trigger.
    // For bar/chip: open below it, right-aligned or left-aligned per `align`.
    const style = variant === 'icon'
      ? { top: rect.top, left: rect.right + 10 }
      : align === 'right'
        ? { top: rect.bottom + 8, right: window.innerWidth - rect.right }
        : { top: rect.bottom + 8, left: rect.left }

    return createPortal(
      <>
        <div
          onClick={() => setOpen(false)}
          style={{ position: 'fixed', inset: 0, zIndex: 900 }}
        />
        <div
          className="anim-fade-down"
          style={{
            position: 'fixed', ...style,
            width: variant === 'icon' ? '230px' : 'min(280px, calc(100vw - 24px))',
            background: panelBg,
            border: `1px solid ${panelBorder}`,
            borderRadius: '12px',
            boxShadow: '0 20px 48px rgba(0,0,0,0.35)',
            zIndex: 901, overflow: 'hidden',
          }}
        >
          <div style={{
            padding: '10px 14px 6px',
            fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em',
            textTransform: 'uppercase', color: mutedText,
          }}>
            Switch Workspace
          </div>

          <div style={{ maxHeight: '260px', overflowY: 'auto', padding: '2px 6px' }}>
            <SwitchRow
              label="All Meetings"
              dotColor={mutedText}
              active={activeWorkspaceId == null}
              onClick={() => pick(null)}
              hoverBg={itemHoverBg} textColor={itemText} accentColor={accentColor}
            />
            {workspaces?.map(ws => (
              <SwitchRow
                key={ws.id}
                label={ws.name}
                dotColor={ws.color || T.accent}
                active={activeWorkspaceId === ws.id}
                onClick={() => pick(ws.id)}
                hoverBg={itemHoverBg} textColor={itemText} accentColor={accentColor}
              />
            ))}
            {workspaces?.length === 0 && (
              <div style={{ padding: '10px 10px 12px', fontSize: '12px', color: mutedText }}>
                No workspaces yet.
              </div>
            )}
          </div>

          <div style={{ height: 1, background: panelBorder }} />
          <button
            onClick={() => { setOpen(false); navigate('/app/workspaces') }}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
              padding: '11px 14px', background: 'none', border: 'none',
              cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
              fontSize: '12.5px', fontWeight: 650, color: accentColor,
            }}
            onMouseEnter={e => e.currentTarget.style.background = itemHoverBg}
            onMouseLeave={e => e.currentTarget.style.background = 'none'}
          >
            <Layers size={13} /> Manage Workspaces
          </button>
        </div>
      </>,
      document.body,
    )
  }

  // ── Trigger — icon-only (collapsed rail) ────────────────────────────────
  if (variant === 'icon') {
    return (
      <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
        <button
          ref={triggerRef}
          onClick={() => setOpen(v => !v)}
          title={activeWorkspace ? activeWorkspace.name : 'All Meetings — switch workspace'}
          style={{
            width: 30, height: 30, borderRadius: '9px',
            background: isDark ? 'rgba(255,255,255,0.05)' : T.accentBg,
            border: `1px solid ${activeWorkspace ? `${color}55` : (isDark ? 'rgba(255,255,255,0.10)' : T.border2)}`,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <span style={{
            width: 9, height: 9, borderRadius: '50%',
            background: color,
            boxShadow: activeWorkspace ? `0 0 6px ${color}99` : 'none',
          }} />
        </button>
        {open && <Panel />}
      </div>
    )
  }

  // ── Trigger — compact chip (mobile top bar) ─────────────────────────────
  if (variant === 'chip') {
    return (
      <div style={{ position: 'relative' }}>
        <button
          ref={triggerRef}
          onClick={() => setOpen(v => !v)}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            padding: '6px 10px 6px 8px', borderRadius: '99px',
            background: isDark ? 'rgba(255,255,255,0.06)' : T.accentBg,
            border: `1px solid ${isDark ? 'rgba(255,255,255,0.10)' : T.border2}`,
            cursor: 'pointer', maxWidth: '160px',
          }}
        >
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0 }} />
          <span style={{
            fontSize: '12px', fontWeight: 650,
            color: T.text,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
          }}>
            {activeWorkspace ? activeWorkspace.name : 'All Meetings'}
          </span>
          <ChevronDown size={11} color={mutedText} style={{ flexShrink: 0 }} />
        </button>
        {open && <Panel />}
      </div>
    )
  }

  // ── Trigger — full bar (sidebar, expanded) ──────────────────────────────
  return (
    <div style={{ position: 'relative' }}>
      <button
        ref={triggerRef}
        onClick={() => setOpen(v => !v)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
          padding: '7px 9px', borderRadius: '9px',
          background: isDark ? 'rgba(255,255,255,0.045)' : T.accentBg,
          border: `1px solid ${isDark ? 'rgba(255,255,255,0.08)' : T.border2}`,
          cursor: 'pointer', fontFamily: 'inherit',
        }}
      >
        <span style={{
          width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
          background: color,
          boxShadow: activeWorkspace ? `0 0 6px ${color}99` : 'none',
        }} />
        <span style={{
          flex: 1, minWidth: 0, textAlign: 'left',
          fontSize: '12px', fontWeight: 700, letterSpacing: '0.01em',
          color: T.text,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {activeWorkspace ? activeWorkspace.name : 'All Meetings'}
        </span>
        <ChevronDown size={13} color={mutedText} style={{ flexShrink: 0 }} />
      </button>
      {open && <Panel />}
    </div>
  )
}

function SwitchRow({ label, dotColor, active, onClick, hoverBg, textColor, accentColor }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%', display: 'flex', alignItems: 'center', gap: '9px',
        padding: '8px 8px', borderRadius: '8px',
        background: 'none', border: 'none',
        cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
      }}
      onMouseEnter={e => e.currentTarget.style.background = hoverBg}
      onMouseLeave={e => e.currentTarget.style.background = 'none'}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
      <span style={{
        flex: 1, fontSize: '13px', fontWeight: 600, color: textColor,
        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
      }}>
        {label}
      </span>
      {active && <Check size={13} color={accentColor} style={{ flexShrink: 0 }} />}
    </button>
  )
}