// client/src/pages/Support.jsx

import { useState } from 'react'
import {
  ChevronDown, ChevronUp, Send,
  MessageSquare, Mail, CheckCircle,
  AlertCircle, HelpCircle, Mic
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { sendContactForm } from '../api/client'
import Navbar from '../components/Navbar'

// ── FAQ data ───────────────────────────────────────────────────────────────────
const FAQS = [
  {
    category: 'Getting Started',
    items: [
      {
        q: 'How does Summly work?',
        a: 'Upload any audio or video recording, or paste a YouTube URL. Summly transcribes it using Whisper AI, then runs four specialized AI agents in sequence — extracting a summary, decisions, action items, and topics. Everything is stored and searchable.',
      },
      {
        q: 'What file formats are supported?',
        a: 'Audio: MP3, WAV, M4A, AAC, FLAC. Video: MP4, MKV, AVI, MOV, WEBM. Maximum file size is 500MB. You can also paste any public YouTube URL.',
      },
      {
        q: 'How long does processing take?',
        a: 'Typically 1–5 minutes depending on file length and server load. A 1-hour meeting usually takes 2–3 minutes. You can see live progress updates during processing.',
      },
      {
        q: 'Do I need to create an account?',
        a: 'You can explore the Demo meeting without an account. To upload and save your own meetings, a free account is required. Registration takes under 30 seconds.',
      },
    ],
  },
  {
    category: 'AI Features',
    items: [
      {
        q: 'How does the AI chat work?',
        a: 'Summly uses a hybrid RAG (Retrieval Augmented Generation) system. It combines vector similarity search with BM25 keyword search to find the most relevant transcript sections, then uses LLaMA 3.3 70B to generate accurate, grounded answers.',
      },
      {
        q: 'Can I search across multiple meetings?',
        a: 'Yes. The Cross-Meeting Search feature lets you ask questions across your entire meeting history. For example: "What decisions were made about deployment?" will search all your meetings.',
      },
      {
        q: 'How accurate is the transcription?',
        a: 'Summly uses OpenAI Whisper (base model) which achieves high accuracy on clear audio. Performance depends on audio quality, accents, and background noise. For best results, use clear recordings with minimal background noise.',
      },
      {
        q: 'What AI model powers the intelligence features?',
        a: 'Transcription uses OpenAI Whisper. Meeting intelligence (summaries, decisions, action items) uses LLaMA 3.3 70B via Groq API. Embeddings use all-MiniLM-L6-v2 from HuggingFace.',
      },
    ],
  },
  {
    category: 'Privacy & Security',
    items: [
      {
        q: 'Is my data secure?',
        a: 'Your meetings are stored securely and linked to your account with JWT authentication. Only you can access your meetings. Passwords are hashed with bcrypt and never stored in plain text.',
      },
      {
        q: 'Can other users see my meetings?',
        a: 'No. Every meeting is scoped to your user account. Other users cannot access, search, or view your meetings in any way.',
      },
      {
        q: 'Can I delete my data?',
        a: 'Yes. You can delete individual meetings from the meetings page. Account deletion with full data removal is available in Settings.',
      },
    ],
  },
  {
    category: 'Pricing & Plans',
    items: [
      {
        q: 'Is Summly really free?',
        a: 'Yes — completely free. No credit card, no trial period, no premium tier, no hidden fees. Create an account and get full access to all features forever.',
      },
      {
        q: 'Are there upload limits?',
        a: 'Authenticated users get unlimited uploads. Files must be under 500MB. There are no limits on the number of meetings, AI chat questions, or searches.',
      },
    ],
  },
]

// ── FAQ accordion ──────────────────────────────────────────────────────────────
function FaqItem({ q, a, T }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      borderBottom: `1px solid ${T.border}`,
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', padding: '18px 0',
          display: 'flex', alignItems: 'flex-start',
          justifyContent: 'space-between', gap: '16px',
          background: 'none', border: 'none',
          cursor: 'pointer', textAlign: 'left',
          fontFamily: 'var(--font)',
        }}
      >
        <span style={{
          fontSize: '15px', fontWeight: 600,
          color: T.text, lineHeight: 1.45, flex: 1,
        }}>
          {q}
        </span>
        <span style={{ flexShrink: 0, marginTop: '2px' }}>
          {open
            ? <ChevronUp size={17} color={T.accent} />
            : <ChevronDown size={17} color={T.text3} />
          }
        </span>
      </button>
      {open && (
        <div className="anim-fade-in" style={{
          paddingBottom: '18px',
          fontSize: '14px', color: T.text3,
          lineHeight: 1.75, fontWeight: 400,
        }}>
          {a}
        </div>
      )}
    </div>
  )
}

// ── Contact form ───────────────────────────────────────────────────────────────
function ContactForm({ T }) {
  const [form, setForm] = useState({
    name: '', email: '', subject: '', message: '',
  })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error,   setError]   = useState(null)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await sendContactForm(
        form.name, form.email, form.subject, form.message
      )
      setSuccess(true)
      setForm({ name: '', email: '', subject: '', message: '' })
    } catch (err) {
      setError(err.message || 'Failed to send. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%', padding: '11px 14px',
    borderRadius: '10px',
    border: `1px solid ${T.inputBorder}`,
    background: T.inputBg, color: T.text,
    fontSize: '14px', outline: 'none',
    fontFamily: 'var(--font)',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
  }

  if (success) {
    return (
      <div className="anim-fade-up" style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', textAlign: 'center',
        padding: '48px 32px',
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: '20px',
        boxShadow: T.cardShadow,
      }}>
        <div style={{
          width: '56px', height: '56px', borderRadius: '16px',
          background: T.emeraldBg, marginBottom: '18px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <CheckCircle size={28} color={T.emerald} />
        </div>
        <div style={{
          fontSize: '20px', fontWeight: 800,
          color: T.text, letterSpacing: '-0.03em',
          marginBottom: '8px',
        }}>
          Message sent!
        </div>
        <div style={{
          fontSize: '14px', color: T.text3,
          lineHeight: 1.65, marginBottom: '24px',
        }}>
          Thanks for reaching out. We'll get back to you soon.
        </div>
        <button
          onClick={() => setSuccess(false)}
          style={{
            padding: '9px 20px', borderRadius: '9px',
            background: T.surface2, border: `1px solid ${T.border}`,
            color: T.text2, fontSize: '13px', fontWeight: 600,
            cursor: 'pointer', fontFamily: 'var(--font)',
          }}
        >
          Send another message
        </button>
      </div>
    )
  }

  return (
    <div style={{
      background: T.surface, border: `1px solid ${T.border}`,
      borderRadius: '20px', padding: '32px',
      boxShadow: T.cardShadow,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        marginBottom: '24px',
      }}>
        <div style={{
          width: '40px', height: '40px', borderRadius: '11px',
          background: T.accentBg,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Mail size={19} color={T.accentLight} />
        </div>
        <div>
          <div style={{
            fontSize: '17px', fontWeight: 750,
            color: T.text, letterSpacing: '-0.03em',
          }}>
            Send a message
          </div>
          <div style={{ fontSize: '13px', color: T.text3, marginTop: '1px' }}>
            We typically respond within 24 hours
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '12px 14px', borderRadius: '10px',
          background: T.dangerBg, border: `1px solid ${T.danger}44`,
          marginBottom: '18px',
        }}>
          <AlertCircle size={15} color={T.danger} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: '13px', color: T.danger }}>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '14px', marginBottom: '14px',
        }}>
          {/* Name */}
          <div>
            <label style={{
              display: 'block', fontSize: '12px',
              fontWeight: 650, color: T.text2, marginBottom: '6px',
              letterSpacing: '0.01em',
            }}>
              Full name
            </label>
            <input
              type="text"
              value={form.name}
              onChange={e => set('name', e.target.value)}
              placeholder="Pankaj Thakur"
              required
              style={inputStyle}
              onFocus={e => {
                e.target.style.borderColor = T.borderFocus
                e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}`
              }}
              onBlur={e => {
                e.target.style.borderColor = T.inputBorder
                e.target.style.boxShadow = 'none'
              }}
            />
          </div>
          {/* Email */}
          <div>
            <label style={{
              display: 'block', fontSize: '12px',
              fontWeight: 650, color: T.text2, marginBottom: '6px',
            }}>
              Email address
            </label>
            <input
              type="email"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              placeholder="you@example.com"
              required
              style={inputStyle}
              onFocus={e => {
                e.target.style.borderColor = T.borderFocus
                e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}`
              }}
              onBlur={e => {
                e.target.style.borderColor = T.inputBorder
                e.target.style.boxShadow = 'none'
              }}
            />
          </div>
        </div>

        {/* Subject */}
        <div style={{ marginBottom: '14px' }}>
          <label style={{
            display: 'block', fontSize: '12px',
            fontWeight: 650, color: T.text2, marginBottom: '6px',
          }}>
            Subject
          </label>
          <input
            type="text"
            value={form.subject}
            onChange={e => set('subject', e.target.value)}
            placeholder="Question about..."
            required
            style={inputStyle}
            onFocus={e => {
              e.target.style.borderColor = T.borderFocus
              e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}`
            }}
            onBlur={e => {
              e.target.style.borderColor = T.inputBorder
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        {/* Message */}
        <div style={{ marginBottom: '20px' }}>
          <label style={{
            display: 'block', fontSize: '12px',
            fontWeight: 650, color: T.text2, marginBottom: '6px',
          }}>
            Message
          </label>
          <textarea
            value={form.message}
            onChange={e => set('message', e.target.value)}
            placeholder="Tell us what's on your mind..."
            required
            rows={5}
            style={{
              ...inputStyle,
              resize: 'vertical',
              minHeight: '120px',
            }}
            onFocus={e => {
              e.target.style.borderColor = T.borderFocus
              e.target.style.boxShadow = `0 0 0 3px ${T.accentBg}`
            }}
            onBlur={e => {
              e.target.style.borderColor = T.inputBorder
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        <button
          type="submit"
          disabled={
            loading || !form.name || !form.email ||
            !form.subject || !form.message
          }
          style={{
            width: '100%', padding: '12px',
            borderRadius: '11px',
            background: loading || !form.name || !form.email ||
              !form.subject || !form.message
              ? T.surface2 : T.btnGrad,
            border: 'none',
            color: loading || !form.name || !form.email ||
              !form.subject || !form.message
              ? T.text4 : '#fff',
            fontSize: '14px', fontWeight: 700,
            cursor: 'pointer',
            display: 'flex', alignItems: 'center',
            justifyContent: 'center', gap: '8px',
            fontFamily: 'var(--font)',
            boxShadow: loading ? 'none' : T.btnShadow,
            transition: 'all 0.15s ease',
          }}
        >
          {loading
            ? <><span className="spinner" style={{
                width: '14px', height: '14px',
                borderColor: T.text3, borderTopColor: 'transparent',
              }} /> Sending...</>
            : <><Send size={14} /> Send Message</>
          }
        </button>
      </form>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────
export default function Support() {
  const { T, isDark } = useTheme()
  const [activeCategory, setActiveCategory] = useState('Getting Started')

  const categories = FAQS.map(f => f.category)
  const activeFaqs = FAQS.find(f => f.category === activeCategory)?.items || []

  return (
    <div style={{ background: T.bg, minHeight: '100vh' }}>
      <Navbar />

      {/* ── Hero ── */}
      <section style={{
        padding: '120px 32px 80px',
        textAlign: 'center',
        background: isDark ? T.surface : T.surface2,
        borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ maxWidth: '640px', margin: '0 auto' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '5px 14px', borderRadius: '99px',
            background: T.accentBg, border: `1px solid ${T.accent}33`,
            fontSize: '12px', fontWeight: 700, color: T.accentLight,
            marginBottom: '20px',
          }}>
            <HelpCircle size={13} /> Help & Support
          </div>
          <h1 style={{
            fontSize: 'clamp(30px, 5vw, 48px)',
            fontWeight: 800, letterSpacing: '-0.04em',
            color: T.text, margin: '0 0 14px',
          }}>
            How can we help?
          </h1>
          <p style={{
            fontSize: '17px', color: T.text3,
            lineHeight: 1.65, margin: 0,
          }}>
            Find answers to common questions or send us a message.
          </p>
        </div>
      </section>

      <div style={{
        maxWidth: '1100px', margin: '0 auto',
        padding: '64px 32px',
      }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '1fr 1fr',
          gap: '48px', alignItems: 'start',
        }}>

          {/* ── Left: FAQ ── */}
          <div>
            <div style={{
              fontSize: '13px', fontWeight: 700,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: T.text3, marginBottom: '16px',
            }}>
              Frequently Asked Questions
            </div>

            {/* Category tabs */}
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: '6px',
              marginBottom: '24px',
            }}>
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  style={{
                    padding: '6px 14px', borderRadius: '99px',
                    fontSize: '12.5px', fontWeight: 600,
                    color: activeCategory === cat ? T.navActiveText : T.text3,
                    background: activeCategory === cat ? T.navActiveBg : T.surface,
                    border: `1px solid ${activeCategory === cat
                      ? T.navActiveBorder : T.border}`,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                    fontFamily: 'var(--font)',
                  }}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* FAQ items */}
            <div style={{
              background: T.surface,
              border: `1px solid ${T.border}`,
              borderRadius: '16px',
              padding: '4px 24px',
              boxShadow: T.cardShadow,
            }}>
              {activeFaqs.map(item => (
                <FaqItem key={item.q} q={item.q} a={item.a} T={T} />
              ))}
            </div>

            {/* Still have questions */}
            <div style={{
              marginTop: '20px', padding: '18px 20px',
              background: T.accentBg, border: `1px solid ${T.accent}22`,
              borderRadius: '14px',
              display: 'flex', alignItems: 'center', gap: '14px',
            }}>
              <MessageSquare size={20} color={T.accentLight} style={{ flexShrink: 0 }} />
              <div>
                <div style={{
                  fontSize: '13px', fontWeight: 700,
                  color: T.text, marginBottom: '2px',
                }}>
                  Still have questions?
                </div>
                <div style={{ fontSize: '12.5px', color: T.text3 }}>
                  Use the contact form to reach us directly.
                </div>
              </div>
            </div>
          </div>

          {/* ── Right: Contact form ── */}
          <div>
            <div style={{
              fontSize: '13px', fontWeight: 700,
              letterSpacing: '0.1em', textTransform: 'uppercase',
              color: T.text3, marginBottom: '16px',
            }}>
              Contact Us
            </div>
            <ContactForm T={T} />

            {/* Quick info */}
            <div style={{
              marginTop: '16px',
              display: 'flex', flexDirection: 'column', gap: '10px',
            }}>
              {[
                { icon: <Mail size={15} />,        text: 'pankajthakur.dev01@gmail.com',    color: T.accent  },
                { icon: <CheckCircle size={15} />, text: 'Usually replies in 24h', color: T.emerald },
                { icon: <Mic size={15} />,         text: 'Built by Pankaj Thakur', color: T.purple  },
              ].map(item => (
                <div key={item.text} style={{
                  display: 'flex', alignItems: 'center', gap: '10px',
                  padding: '10px 14px', borderRadius: '10px',
                  background: T.surface, border: `1px solid ${T.border}`,
                }}>
                  <span style={{ color: item.color, flexShrink: 0 }}>
                    {item.icon}
                  </span>
                  <span style={{
                    fontSize: '13px', color: T.text2, fontWeight: 500,
                  }}>
                    {item.text}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}