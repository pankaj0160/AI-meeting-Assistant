// client/src/pages/Settings.jsx

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  User, Lock, Palette, Database,
  LogOut, Save, AlertCircle,
  CheckCircle, Eye, EyeOff, Trash2,
  Download, Sun, Moon, Info
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import {
  apiUpdateProfile, apiChangePassword
} from '../api/client'
import { PageHeader, Card, Button, Divider } from '../components/ui'

// ── Section wrapper ────────────────────────────────────────────────────────────
function SettingsSection({ icon, title, desc, children, T }) {
  return (
    <div style={{ marginBottom: '28px' }}>
      <div style={{
        display: 'flex', alignItems: 'flex-start', gap: '14px',
        marginBottom: '18px',
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
          <div style={{ fontSize: '13px', color: T.text3, marginTop: '2px' }}>
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
      <label style={{
        display: 'block', fontSize: '12.5px',
        fontWeight: 650, color: T.text2, marginBottom: '7px',
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
        <div style={{
          fontSize: '12px', color: T.text4,
          marginTop: '5px',
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
    <div className="anim-fade-up" style={{
      display: 'flex', alignItems: 'center', gap: '10px',
      padding: '11px 14px', borderRadius: '10px',
      background: config.bg, border: `1px solid ${config.color}44`,
      marginBottom: '18px',
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

  // Profile form
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileAlert,   setProfileAlert]   = useState(null)

  // Password form
  const [currentPw,  setCurrentPw]  = useState('')
  const [newPw,      setNewPw]      = useState('')
  const [confirmPw,  setConfirmPw]  = useState('')
  const [showPws,    setShowPws]    = useState(false)
  const [pwLoading,  setPwLoading]  = useState(false)
  const [pwAlert,    setPwAlert]    = useState(null)

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

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage your account, security, and preferences."
      />

      <div style={{ maxWidth: '640px' }}>

        {/* ── Profile ── */}
        <SettingsSection
          icon={<User size={18} color={T.accentLight} />}
          title="Profile"
          desc="Update your name and account information."
          T={T}
        >
          {/* Avatar */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '16px',
            marginBottom: '24px',
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
              <div style={{
                fontSize: '15px', fontWeight: 700,
                color: T.text, marginBottom: '3px',
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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
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

          <div style={{ marginTop: '18px' }}>
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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
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

          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between', marginTop: '18px',
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
          <div style={{
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{
                fontSize: '14px', fontWeight: 600, color: T.text,
                marginBottom: '3px',
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

        {/* ── Data ── */}
        <SettingsSection
          icon={<Database size={18} color={T.accentLight} />}
          title="Data & Export"
          desc="Manage your meeting data."
          T={T}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', gap: '16px',
            }}>
              <div>
                <div style={{
                  fontSize: '14px', fontWeight: 600, color: T.text,
                  marginBottom: '3px',
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
                onClick={() => alert('Export feature coming soon.')}
              >
                Export
              </Button>
            </div>

            <Divider />

            <div style={{
              padding: '14px 16px', borderRadius: '12px',
              background: T.dangerBg, border: `1px solid ${T.danger}33`,
            }}>
              <div style={{
                display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', gap: '16px',
              }}>
                <div>
                  <div style={{
                    fontSize: '14px', fontWeight: 600,
                    color: T.danger, marginBottom: '3px',
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
                  onClick={() => alert('Account deletion coming soon.')}
                >
                  Delete
                </Button>
              </div>
            </div>
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
            { label: 'Version',       value: 'v4.0.0'            },
            { label: 'Backend',       value: 'FastAPI + Python'   },
            { label: 'AI Model',      value: 'LLaMA 3.3 70B'     },
            { label: 'Transcription', value: 'OpenAI Whisper'     },
            { label: 'Vector DB',     value: 'ChromaDB'           },
            { label: 'Embeddings',    value: 'all-MiniLM-L6-v2'  },
            { label: 'Built by',      value: 'Pankaj Thakur'      },
          ].map((item, i, arr) => (
            <div key={item.label}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '12px 0',
              }}>
                <span style={{
                  fontSize: '13.5px', fontWeight: 500, color: T.text3,
                }}>
                  {item.label}
                </span>
                <span style={{
                  fontSize: '13.5px', fontWeight: 650, color: T.text,
                }}>
                  {item.value}
                </span>
              </div>
              {i < arr.length - 1 && (
                <div style={{ height: '1px', background: T.border }} />
              )}
            </div>
          ))}
        </SettingsSection>

        {/* ── Sign out ── */}
        <div style={{
          padding: '20px 24px',
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: '16px', boxShadow: T.cardShadow,
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', gap: '16px',
        }}>
          <div>
            <div style={{
              fontSize: '14px', fontWeight: 600, color: T.text,
              marginBottom: '2px',
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