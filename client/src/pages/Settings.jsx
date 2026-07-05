// client/src/pages/Settings.jsx

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  User, Lock, Palette, Database,
  LogOut, Save, AlertCircle,
  CheckCircle, Eye, EyeOff, Trash2,
  Download, Sun, Moon, Info, Sparkles
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import {
  apiUpdateProfile, apiChangePassword,
  exportMyData, deleteMyAccount,
  vacuumOrphanedChunks,
} from '../api/client'
import { PageHeader, Card, Button, Divider } from '../components/ui'
import { useToast } from '../components/Toast'

// ── Spacing scale (px) ────────────────────────────────────────────────────────
// sp1=4  sp2=8  sp3=12  sp4=16  sp5=20  sp6=24  sp7=28  sp8=32  sp10=40
//
// Section rhythm:
//   Between sections (SettingsSection):  40px  (sp10)
//   Within section header (icon → text): 14px
//   Within Card children (input gap):    16px  (sp4)
//   Label → field gap:                   8px   (sp2)
//   Field → hint gap:                    8px   (sp2)
//   Alert → first field:                 20px  (sp5)
//   Last field → action button row:      20px  (sp5)
//   Row padding in "Sign out" block:     22px 24px


// ── Section wrapper ────────────────────────────────────────────────────────────
function SettingsSection({ icon, title, desc, children, T }) {
  return (
    // 40px between sections creates clear visual grouping at page scan level
    <div style={{ marginBottom: '40px' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: '14px',
        marginBottom: '16px', // 16px between section header and its card
      }}>
        <div style={{
          width: '38px', height: '38px', borderRadius: '10px',
          background: T.accentBg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {icon}
        </div>
        <div>
          <div style={{
            fontSize: '16px', fontWeight: 700,
            color: T.text, letterSpacing: '-0.02em',
          }}>
            {title}
          </div>
          {/* 4px between title and desc — tight relationship, same semantic block */}
          <div style={{ fontSize: '13px', color: T.text3, marginTop: '4px' }}>
            {desc}
          </div>
        </div>
      </div>
      <Card>{children}</Card>
    </div>
  )
}


// ── Input ──────────────────────────────────────────────────────────────────────
function Input({ label, value, onChange, type = 'text', placeholder, disabled, hint }) {
  const { T } = useTheme()
  const [focused, setFocused] = useState(false)
  return (
    <div>
      {/* 8px below label before the field — distinct but not overspacious */}
      <label style={{
        display: 'block', fontSize: '12.5px',
        fontWeight: 650, color: T.text2, marginBottom: '8px',
      }}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        style={{
          width: '100%', padding: '11px 14px',
          borderRadius: '10px',
          border: `1px solid ${focused ? T.borderFocus : T.inputBorder}`,
          background: disabled ? T.surface2 : T.inputBg,
          color: disabled ? T.text3 : T.text,
          fontSize: '14px', outline: 'none',
          boxShadow: focused ? `0 0 0 3px ${T.accentBg}` : 'none',
          transition: 'all 0.15s ease',
          fontFamily: 'var(--font)',
          cursor: disabled ? 'not-allowed' : 'text',
        }}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      />
      {hint && (
        // 8px between field and hint keeps them clearly associated
        <div style={{
          fontSize: '12px', color: T.text4,
          marginTop: '8px',
        }}>
          {hint}
        </div>
      )}
    </div>
  )
}


// ── Alert ──────────────────────────────────────────────────────────────────────
function Alert({ type, message, T }) {
  const config = {
    success: { color: T.emerald, bg: T.emeraldBg, icon: <CheckCircle size={15} /> },
    error:   { color: T.danger,  bg: T.dangerBg,  icon: <AlertCircle size={15} /> },
  }[type]

  return (
    // 20px below alert before first field: alert is visually separated from form
    <div className="anim-fade-up" style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '12px 14px', borderRadius: '10px',
      background: config.bg, border: `1px solid ${config.color}44`,
      marginBottom: '20px',
    }}>
      <span style={{ color: config.color, flexShrink: 0 }}>{config.icon}</span>
      <span style={{ fontSize: '13px', color: config.color, fontWeight: 500 }}>
        {message}
      </span>
    </div>
  )
}


// ── Main ───────────────────────────────────────────────────────────────────────
export default function Settings() {
  const { T, isDark, toggle } = useTheme()
  const { user, logout, updateUser } = useAuth()
  const navigate = useNavigate()
  const { toast } = useToast()

  // Profile form
  const [fullName,       setFullName]       = useState(user?.full_name || '')
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileAlert,   setProfileAlert]   = useState(null)

  // Password form
  const [currentPw, setCurrentPw] = useState('')
  const [newPw,     setNewPw]     = useState('')
  const [confirmPw, setConfirmPw] = useState('')
  const [showPws,   setShowPws]   = useState(false)
  const [pwLoading, setPwLoading] = useState(false)
  const [pwAlert,   setPwAlert]   = useState(null)

  // Data export + account delete
  const [exporting,       setExporting]       = useState(false)
  const [vacuuming,       setVacuuming]       = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteConfirm,   setDeleteConfirm]   = useState('')
  const [deleting,        setDeleting]        = useState(false)

  // Avatar initial
  const initial = user?.full_name?.charAt(0).toUpperCase() || '?'

  // ── Profile save ───────────────────────────────────────────────────────────
  const saveProfile = async () => {
    if (!fullName.trim()) return
    setProfileLoading(true)
    setProfileAlert(null)
    try {
      const updated = await apiUpdateProfile({ full_name: fullName.trim() })
      updateUser(updated)
      setProfileAlert({ type: 'success', message: 'Profile updated successfully.' })
    } catch (err) {
      setProfileAlert({ type: 'error', message: err.message || 'Update failed.' })
    } finally {
      setProfileLoading(false)
    }
  }

  // ── Password save ──────────────────────────────────────────────────────────
  const savePassword = async () => {
    if (newPw !== confirmPw) {
      setPwAlert({ type: 'error', message: 'New passwords do not match.' })
      return
    }
    if (newPw.length < 8) {
      setPwAlert({ type: 'error', message: 'Password must be at least 8 characters.' })
      return
    }
    setPwLoading(true)
    setPwAlert(null)
    try {
      await apiChangePassword(currentPw, newPw)
      setPwAlert({ type: 'success', message: 'Password changed successfully.' })
      setCurrentPw(''); setNewPw(''); setConfirmPw('')
    } catch (err) {
      setPwAlert({ type: 'error', message: err.message || 'Password change failed.' })
    } finally {
      setPwLoading(false)
    }
  }

  // ── Logout ─────────────────────────────────────────────────────────────────
  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  // Export my data — downloads a JSON file of all meetings/intelligence
  const handleExportData = async () => {
    setExporting(true)
    try {
      const blob = await exportMyData()
      const url  = URL.createObjectURL(blob)
      const a    = Object.assign(document.createElement('a'), {
        href:     url,
        download: `summly_export_${new Date().toISOString().slice(0,10)}.json`,
      })
      a.click()
      URL.revokeObjectURL(url)
      toast.success('Export downloaded', 'Your data has been saved as a JSON file.')
    } catch (e) {
      toast.error('Export failed', e.message)
    } finally {
      setExporting(false)
    }
  }

  // FIX: lets users clean up ChromaDB vectors left behind by meetings that
  // were deleted directly in Supabase (before DELETE /meetings/{id}
  // existed). Those orphaned vectors can surface in chat under a
  // completely different, currently-active meeting that happens to share
  // the old one's meeting_id. Safe to run any time — it only ever removes
  // vectors whose meeting_id has zero matching row in the database.
  const handleVacuum = async () => {
    setVacuuming(true)
    try {
      const res = await vacuumOrphanedChunks()
      const parts = []
      if (res.chunks_fixed) parts.push(`repaired ownership on ${res.chunks_fixed} chunk${res.chunks_fixed !== 1 ? 's' : ''}`)
      if (res.orphaned_meeting_ids?.length) parts.push(`removed ${res.chunks_deleted} orphaned chunk${res.chunks_deleted !== 1 ? 's' : ''} left over from ${res.orphaned_meeting_ids.length} deleted meeting${res.orphaned_meeting_ids.length !== 1 ? 's' : ''}`)
      if (parts.length) {
        toast.success('Cleanup complete', parts.join(' and ') + '.')
      } else {
        toast.success('Nothing to clean up', 'No issues found — everything is in sync.')
      }
    } catch (e) {
      toast.error('Cleanup failed', e.message)
    } finally {
      setVacuuming(false)
    }
  }

  // Delete account — requires typing "DELETE" to confirm
  const handleDeleteAccount = async () => {
    if (deleteConfirm !== 'DELETE') return
    setDeleting(true)
    try {
      await deleteMyAccount('DELETE')
      toast.success('Account deleted', 'Your account has been permanently removed.')
      logout()
      navigate('/', { replace: true })
    } catch (e) {
      toast.error('Delete failed', e.message)
      setDeleting(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage your account, security, and preferences."
      />

      {/* Content centered on page — PageHeader remains full-width above */}
      <div style={{ maxWidth: '640px', margin: '0 auto' }}>

        {/* ── Profile ── */}
        <SettingsSection
          icon={<User size={18} color={T.accentLight} />}
          title="Profile"
          desc="Update your name and account information."
          T={T}
        >
          {/* Avatar block — 28px below before inputs for visual breathing room */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '16px',
            marginBottom: '28px',
          }}>
            <div style={{
              width: '56px', height: '56px', borderRadius: '50%',
              background: T.btnGrad, boxShadow: T.btnShadow,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '22px', fontWeight: 800, color: '#fff',
              flexShrink: 0,
            }}>
              {initial}
            </div>
            <div>
              {/* 4px between name and email — tightly grouped identity info */}
              <div style={{
                fontSize: '15px', fontWeight: 700,
                color: T.text, marginBottom: '4px',
              }}>
                {user?.full_name}
              </div>
              <div style={{ fontSize: '13px', color: T.text3 }}>
                {user?.email}
              </div>
            </div>
          </div>

          {profileAlert && (
            <Alert type={profileAlert.type} message={profileAlert.message} T={T} />
          )}

          {/* 16px gap between form fields (sp4) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <Input
              label="Full name"
              value={fullName}
              onChange={setFullName}
              placeholder="Your full name"
            />
            <Input
              label="Email address"
              value={user?.email || ''}
              onChange={() => {}}
              disabled
              hint="Email cannot be changed."
            />
          </div>

          {/* 20px above action button — clear separation from fields */}
          <div style={{ marginTop: '20px' }}>
            <Button
              onClick={saveProfile}
              loading={profileLoading}
              disabled={!fullName.trim() || fullName === user?.full_name}
              icon={<Save size={14} />}
              size="sm"
            >
              Save Changes
            </Button>
          </div>
        </SettingsSection>

        {/* ── Security ── */}
        <SettingsSection
          icon={<Lock size={18} color={T.accentLight} />}
          title="Security"
          desc="Change your password to keep your account safe."
          T={T}
        >
          {pwAlert && (
            <Alert type={pwAlert.type} message={pwAlert.message} T={T} />
          )}

          {/* 16px gap between password fields */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ position: 'relative' }}>
              <Input
                label="Current password"
                value={currentPw}
                onChange={setCurrentPw}
                type={showPws ? 'text' : 'password'}
                placeholder="••••••••"
              />
            </div>
            <Input
              label="New password"
              value={newPw}
              onChange={setNewPw}
              type={showPws ? 'text' : 'password'}
              placeholder="Min. 8 characters"
              hint={newPw.length > 0 && newPw.length < 8 ? 'Too short' : ''}
            />
            <Input
              label="Confirm new password"
              value={confirmPw}
              onChange={setConfirmPw}
              type={showPws ? 'text' : 'password'}
              placeholder="Repeat new password"
            />
          </div>

          {/* 20px above action row — matches profile section rhythm */}
          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', marginTop: '20px',
          }}>
            <button
              onClick={() => setShowPws(s => !s)}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                background: 'none', border: 'none',
                cursor: 'pointer', color: T.text3,
                fontSize: '13px', fontWeight: 500,
                fontFamily: 'var(--font)',
              }}
            >
              {showPws ? <EyeOff size={14} /> : <Eye size={14} />}
              {showPws ? 'Hide' : 'Show'} passwords
            </button>
            <Button
              onClick={savePassword}
              loading={pwLoading}
              disabled={!currentPw || !newPw || !confirmPw}
              icon={<Lock size={14} />}
              size="sm"
            >
              Change Password
            </Button>
          </div>
        </SettingsSection>

        {/* ── Appearance ── */}
        <SettingsSection
          icon={<Palette size={18} color={T.accentLight} />}
          title="Appearance"
          desc="Customize how Summly looks."
          T={T}
        >
          {/* Single-row layout: label+desc on left, toggle on right */}
          {/* No extra padding needed — Card provides internal padding */}
          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', gap: '16px',
          }}>
            <div>
              {/* 4px between "Theme" label and its sub-description */}
              <div style={{
                fontSize: '14px', fontWeight: 600, color: T.text,
                marginBottom: '4px',
              }}>
                Theme
              </div>
              <div style={{ fontSize: '13px', color: T.text3 }}>
                Currently using {isDark ? 'dark' : 'light'} mode
              </div>
            </div>
            <div style={{
              display: 'inline-flex',
              background: T.surface2, border: `1px solid ${T.border}`,
              borderRadius: '11px', padding: '4px', gap: '4px',
              flexShrink: 0, // prevent toggle collapsing on narrow containers
            }}>
              {[
                { val: true,  icon: <Moon size={14} />,  label: 'Dark'  },
                { val: false, icon: <Sun size={14} />,   label: 'Light' },
              ].map(opt => (
                <button
                  key={String(opt.val)}
                  onClick={() => { if (isDark !== opt.val) toggle() }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '7px 14px', borderRadius: '8px',
                    fontSize: '13px', fontWeight: 600,
                    color: isDark === opt.val ? T.text : T.text3,
                    background: isDark === opt.val ? T.surface : 'transparent',
                    border: `1px solid ${isDark === opt.val ? T.border : 'transparent'}`,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                    boxShadow: isDark === opt.val ? T.cardShadow : 'none',
                    fontFamily: 'var(--font)',
                  }}
                >
                  {opt.icon} {opt.label}
                </button>
              ))}
            </div>
          </div>
        </SettingsSection>

        {/* ── Data & Export ── */}
        <SettingsSection
          icon={<Database size={18} color={T.accentLight} />}
          title="Data & Export"
          desc="Manage your meeting data."
          T={T}
        >
          {/* 16px gap between data action items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', gap: '16px',
            }}>
              <div>
                {/* 4px between action title and its description */}
                <div style={{
                  fontSize: '14px', fontWeight: 600, color: T.text,
                  marginBottom: '4px',
                }}>
                  Export all meetings
                </div>
                <div style={{ fontSize: '13px', color: T.text3 }}>
                  Download all your meeting data as JSON
                </div>
              </div>
              <Button
                variant="ghost" size="sm"
                icon={<Download size={13} />}
                onClick={handleExportData}
                loading={exporting}
                style={{ flexShrink: 0 }}
              >
                Export
              </Button>
            </div>

            <Divider />

            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', gap: '16px',
            }}>
              <div>
                <div style={{
                  fontSize: '14px', fontWeight: 600, color: T.text,
                  marginBottom: '4px',
                }}>
                  Clean up orphaned chat data
                </div>
                <div style={{ fontSize: '13px', color: T.text3, lineHeight: 1.5 }}>
                  If a meeting was ever deleted outside the app (directly in the
                  database), leftover chat data from it can persist and
                  occasionally surface in answers about other meetings. This
                  removes anything no longer tied to a meeting you have. Safe to
                  run any time.
                </div>
              </div>
              <Button
                variant="ghost" size="sm"
                icon={<Sparkles size={13} />}
                onClick={handleVacuum}
                loading={vacuuming}
                style={{ flexShrink: 0 }}
              >
                Clean Up
              </Button>
            </div>

            <Divider />

            {/* Danger zone: inner padding creates contained red zone feel */}
            <div style={{
              padding: '16px', borderRadius: '12px',
              background: T.dangerBg, border: `1px solid ${T.danger}33`,
            }}>
              <div style={{
                display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', gap: '16px',
              }}>
                <div>
                  <div style={{
                    fontSize: '14px', fontWeight: 600,
                    color: T.danger, marginBottom: '4px',
                  }}>
                    Delete account
                  </div>
                  <div style={{
                    fontSize: '12.5px', color: T.text3, lineHeight: 1.5,
                  }}>
                    Permanently delete your account and all data.
                    This cannot be undone.
                  </div>
                </div>
                <Button
                  variant="danger" size="sm"
                  icon={<Trash2 size={13} />}
                  onClick={() => setShowDeleteModal(true)}
                  style={{ flexShrink: 0 }}
                >
                  Delete
                </Button>
              </div>
            </div>

            {/* Delete confirmation modal */}
            {showDeleteModal && (
              <div style={{
                position: 'fixed', inset: 0,
                background: 'rgba(0,0,0,0.70)',
                backdropFilter: 'blur(8px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 800, padding: '24px',
              }}>
                <div className="anim-scale-spring" style={{
                  background: T.surface, border: `1px solid ${T.border}`,
                  borderRadius: '18px', width: '100%', maxWidth: '420px',
                  padding: '28px', boxShadow: '0 24px 60px rgba(0,0,0,0.4)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                    <div style={{
                      width: 38, height: 38, borderRadius: '10px',
                      background: `${T.danger}14`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Trash2 size={17} color={T.danger} />
                    </div>
                    <div>
                      <div style={{ fontSize: '15px', fontWeight: 700, color: T.text }}>Delete Account</div>
                      <div style={{ fontSize: '12px', color: T.text3 }}>This cannot be undone.</div>
                    </div>
                  </div>
                  <p style={{ fontSize: '13.5px', color: T.text2, lineHeight: 1.65, marginBottom: '20px' }}>
                    All your meetings, summaries, action items, and workspaces will be permanently deleted.
                    Type <strong style={{ color: T.danger }}>DELETE</strong> to confirm.
                  </p>
                  <input
                    value={deleteConfirm}
                    onChange={e => setDeleteConfirm(e.target.value)}
                    placeholder="Type DELETE to confirm"
                    style={{
                      width: '100%', padding: '10px 13px',
                      borderRadius: '9px', marginBottom: '16px',
                      border: `1px solid ${deleteConfirm === 'DELETE' ? T.danger : T.border}`,
                      background: T.surface2, color: T.text,
                      fontSize: '14px', outline: 'none', fontFamily: 'var(--font)',
                    }}
                  />
                  <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                    <Button variant="ghost" onClick={() => { setShowDeleteModal(false); setDeleteConfirm('') }}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleDeleteAccount}
                      loading={deleting}
                      disabled={deleteConfirm !== 'DELETE'}
                      style={{
                        background: T.danger, borderColor: T.danger,
                        opacity: deleteConfirm !== 'DELETE' ? 0.5 : 1,
                      }}
                    >
                      Delete My Account
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </SettingsSection>

        {/* ── About ── */}
        <SettingsSection
          icon={<Info size={18} color={T.accentLight} />}
          title="About Summly"
          desc="Version and technical information."
          T={T}
        >
          {[
            { label: 'Version',       value: 'v4.0.0'           },
            { label: 'Backend',       value: 'FastAPI + Python'  },
            { label: 'AI Model',      value: 'LLaMA 3.3 70B'    },
            { label: 'Transcription', value: 'OpenAI Whisper'    },
            { label: 'Vector DB',     value: 'ChromaDB'          },
            { label: 'Embeddings',    value: 'all-MiniLM-L6-v2' },
            { label: 'Built by',      value: 'Pankaj Thakur'     },
          ].map((item, i, arr) => (
            <div key={item.label}>
              {/* 14px row padding for readable key-value rows; up from 12px */}
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '14px 0',
              }}>
                <span style={{ fontSize: '13.5px', fontWeight: 500, color: T.text3 }}>
                  {item.label}
                </span>
                <span style={{ fontSize: '13.5px', fontWeight: 650, color: T.text }}>
                  {item.value}
                </span>
              </div>
              {i < arr.length - 1 && (
                <div style={{ height: '1px', background: T.border }} />
              )}
            </div>
          ))}
        </SettingsSection>

        {/* ── Sign out ────────────────────────────────────────────────────── */}
        {/* 22px 24px padding: slightly more vertical than horizontal        */}
        {/* to keep the row feeling balanced at the footer of the page       */}
        <div style={{
          padding: '22px 24px',
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: '16px', boxShadow: T.cardShadow,
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', gap: '16px',
        }}>
          <div>
            {/* 4px between "Signed in as" label and email */}
            <div style={{
              fontSize: '14px', fontWeight: 600, color: T.text,
              marginBottom: '4px',
            }}>
              Signed in as
            </div>
            <div style={{ fontSize: '13px', color: T.text3 }}>
              {user?.email}
            </div>
          </div>
          <button
            onClick={handleLogout}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '7px',
              padding: '9px 18px', borderRadius: '10px',
              fontSize: '13px', fontWeight: 650,
              color: T.danger, background: T.dangerBg,
              border: `1px solid ${T.danger}33`,
              cursor: 'pointer', transition: 'all 0.15s ease',
              fontFamily: 'var(--font)',
              flexShrink: 0,
            }}
            onMouseEnter={e => e.currentTarget.style.background = T.danger + '22'}
            onMouseLeave={e => e.currentTarget.style.background = T.dangerBg}
          >
            <LogOut size={14} /> Sign Out
          </button>
        </div>

      </div>
    </div>
  )
}