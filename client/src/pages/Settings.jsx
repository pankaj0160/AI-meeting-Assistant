// client/src/pages/Settings.jsx

import { useTheme } from '../ThemeContext'
import { PageHeader, Card, Divider } from '../components/ui'
import { Sun, Moon, Info } from 'lucide-react'

function SettingRow({ label, description, children }) {
  const { T } = useTheme()
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      gap: '24px', padding: '18px 0',
      borderBottom: `1px solid ${T.border}`,
    }}>
      <div>
        <div style={{
          fontSize: '15px', fontWeight: 600,
          color: T.text, marginBottom: '3px',
        }}>
          {label}
        </div>
        {description && (
          <div style={{ fontSize: '13px', color: T.text3, lineHeight: 1.5 }}>
            {description}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{children}</div>
    </div>
  )
}

export default function Settings() {
  const { T, isDark, toggle } = useTheme()

  return (
    <div>
      <PageHeader title="Settings" subtitle="Manage your Summly preferences." />

      <div style={{ maxWidth: '640px' }}>

        {/* Appearance */}
        <Card style={{ marginBottom: '20px' }}>
          <div style={{
            fontSize: '13px', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: T.text3, marginBottom: '4px',
          }}>
            Appearance
          </div>
          <SettingRow
            label="Theme"
            description="Switch between dark and light mode."
          >
            <div style={{
              display: 'inline-flex',
              background: T.surface2,
              border: `1px solid ${T.border}`,
              borderRadius: '10px',
              padding: '4px', gap: '4px',
            }}>
              {[
                { val: true,  icon: <Moon size={14} />,  label: 'Dark'  },
                { val: false, icon: <Sun size={14} />,   label: 'Light' },
              ].map(opt => (
                <button
                  key={String(opt.val)}
                  onClick={() => { if (isDark !== opt.val) toggle() }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '7px',
                    padding: '7px 14px', borderRadius: '7px',
                    fontSize: '13px', fontWeight: 600,
                    color: isDark === opt.val ? T.text : T.text3,
                    background: isDark === opt.val ? T.surface : 'transparent',
                    border: `1px solid ${isDark === opt.val ? T.border : 'transparent'}`,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                    boxShadow: isDark === opt.val ? T.cardShadow : 'none',
                  }}
                >
                  {opt.icon}
                  {opt.label}
                </button>
              ))}
            </div>
          </SettingRow>
        </Card>

        {/* About */}
        <Card>
          <div style={{
            fontSize: '13px', fontWeight: 700,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            color: T.text3, marginBottom: '4px',
          }}>
            About
          </div>
          {[
            { label: 'Version',     value: 'v4.0.0 · Phase 4' },
            { label: 'Backend',     value: 'FastAPI + Groq'   },
            { label: 'AI Model',    value: 'LLaMA 3.3 70B'    },
            { label: 'Transcription', value: 'OpenAI Whisper' },
            { label: 'Vector DB',   value: 'ChromaDB'         },
            { label: 'Embeddings',  value: 'all-MiniLM-L6-v2' },
          ].map(item => (
            <div key={item.label} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '14px 0',
              borderBottom: `1px solid ${T.border}`,
              fontSize: '14px',
            }}>
              <span style={{ color: T.text3, fontWeight: 500 }}>{item.label}</span>
              <span style={{ color: T.text,  fontWeight: 600 }}>{item.value}</span>
            </div>
          ))}
        </Card>

      </div>
    </div>
  )
}