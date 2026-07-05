// client/src/pages/Landing.jsx

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Zap, CheckSquare, FileText,
  MessageSquare, BarChart2, Upload,
  ChevronDown, ChevronUp, ArrowRight,
  Shield, Clock, Search, Star,
  Play, Users, TrendingUp, Lock
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'

// ── Animated counter ───────────────────────────────────────────────────────────
function Counter({ target, suffix = '' }) {
  const [count, setCount] = useState(0)
  const elRef   = useRef(null)
  const started = useRef(false)

  useEffect(() => {
    const el = elRef.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true
          const duration = 1200 // ms
          const steps    = 50
          const interval = duration / steps
          const increment = target / steps
          let current = 0

          const iv = setInterval(() => {
            current += increment
            if (current >= target) {
              setCount(target)
              clearInterval(iv)
            } else {
              setCount(Math.floor(current))
            }
          }, interval)
        }
      },
      { threshold: 0.3 }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [target])

  return <span ref={elRef}>{count.toLocaleString()}{suffix}</span>
}

// ── FAQ Item ───────────────────────────────────────────────────────────────────
function FaqItem({ q, a, T }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      transition: 'all 0.15s ease',
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', padding: '20px 0',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', gap: '16px',
          background: 'none', border: 'none',
          cursor: 'pointer', textAlign: 'left',
          fontFamily: 'var(--font)',
        }}
      >
        <span style={{
          fontSize: '16px', fontWeight: 600,
          color: T.text, lineHeight: 1.4,
        }}>
          {q}
        </span>
        {open
          ? <ChevronUp size={18} color={T.accent} style={{ flexShrink: 0 }} />
          : <ChevronDown size={18} color={T.text3} style={{ flexShrink: 0 }} />
        }
      </button>
      {open && (
        <div className="anim-fade-in" style={{
          paddingBottom: '20px',
          fontSize: '15px', color: T.text3,
          lineHeight: 1.7, fontWeight: 400,
        }}>
          {a}
        </div>
      )}
    </div>
  )
}

// ── Feature card ───────────────────────────────────────────────────────────────
function FeatureCard({ icon, title, desc, color, bg, T }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: '28px',
        borderRadius: '18px',
        background: T.surface,
        border: `1px solid ${hovered ? color + '44' : T.border}`,
        boxShadow: hovered ? `0 8px 32px ${color}18` : T.cardShadow,
        transition: 'all 0.2s ease',
        transform: hovered ? 'translateY(-2px)' : 'none',
      }}
    >
      <div style={{
        width: '46px', height: '46px', borderRadius: '12px',
        background: bg, marginBottom: '18px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: '17px', fontWeight: 700,
        color: T.text, letterSpacing: '-0.03em',
        marginBottom: '8px',
      }}>
        {title}
      </div>
      <div style={{
        fontSize: '14px', color: T.text3,
        lineHeight: 1.65, fontWeight: 400,
      }}>
        {desc}
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Landing() {
  const { T, isDark } = useTheme()
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const features = [
    {
      icon: <FileText size={22} color={T.blueText} />,
      title: 'AI Summaries',
      desc: 'Get concise executive summaries of every meeting. No more reading transcripts.',
      color: T.blue, bg: T.blueBg,
    },
    {
      icon: <Zap size={22} color={T.purpleText} />,
      title: 'Decision Tracking',
      desc: 'Every decision made in your meeting is automatically extracted and organized.',
      color: T.purple, bg: T.purpleBg,
    },
    {
      icon: <CheckSquare size={22} color={T.orangeText} />,
      title: 'Action Items',
      desc: 'Tasks, owners and deadlines extracted automatically. Nothing falls through.',
      color: T.orange, bg: T.orangeBg,
    },
    {
      icon: <MessageSquare size={22} color={T.emeraldText} />,
      title: 'AI Chat',
      desc: 'Ask anything about your meetings. Get instant answers powered by RAG.',
      color: T.emerald, bg: T.emeraldBg,
    },
    {
      icon: <Search size={22} color={T.cyanText} />,
      title: 'Cross-Meeting Search',
      desc: 'Search across all your meetings at once. Find any decision or action item.',
      color: T.cyan, bg: T.cyanBg,
    },
    {
      icon: <BarChart2 size={22} color={T.accentLight} />,
      title: 'Analytics',
      desc: 'Track meeting patterns, decision velocity and team productivity over time.',
      color: T.accent, bg: T.accentBg,
    },
  ]

  const faqs = [
    {
      q: 'How does Summly work?',
      a: 'Upload any audio or video file, or paste a YouTube URL. Summly transcribes the audio using Whisper AI, then runs intelligent agents to extract summaries, decisions, action items and topics — all automatically.',
    },
    {
      q: 'What file formats are supported?',
      a: 'Audio: MP3, WAV, M4A, AAC, FLAC. Video: MP4, MKV, AVI, MOV, WEBM. You can also paste any YouTube URL.',
    },
    {
      q: 'Is my data secure?',
      a: 'Your meetings are stored securely and linked to your account. Only you can access your meetings. We never share your data with third parties.',
    },
    {
      q: 'How does the AI chat work?',
      a: 'Summly uses a hybrid RAG system combining vector search and BM25 keyword search to find the most relevant parts of your transcripts, then uses LLaMA 3.3 70B to generate accurate, grounded answers.',
    },
    {
      q: 'Is Summly really free?',
      a: 'Yes — completely free. No credit card, no trial period, no hidden fees. Create an account and get full access to all features forever.',
    },
    {
      q: 'Can I upload videos from Zoom or Teams?',
      a: 'Yes. Export your Zoom or Teams recording as an MP4 file and upload it directly. Summly will extract the audio and process it automatically.',
    },
  ]

  const benefits = [
    { icon: '🚀', label: 'Unlimited uploads' },
    { icon: '💬', label: 'Unlimited AI chat' },
    { icon: '📊', label: 'Full analytics' },
    { icon: '🔍', label: 'Cross-meeting search' },
    { icon: '📥', label: 'Export reports' },
    { icon: '🔒', label: 'Private & secure' },
    { icon: '⚡', label: 'Meeting history' },
    { icon: '✅', label: 'Action item tracking' },
  ]

  return (
    <div className="page-enter" style={{
      background: T.bg, minHeight: '100vh',
      transition: 'background 0.18s ease',
    }}>
      <Navbar />

      {/* ── HERO ─────────────────────────────────────────────────────────────── */}
      <section style={{
        minHeight: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '120px 32px 80px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>

        {/* Background glow */}
        <div style={{
          position: 'absolute',
          top: '20%', left: '50%',
          transform: 'translateX(-50%)',
          width: '600px', height: '400px',
          background: isDark ? 'radial-gradient(ellipse, rgba(16,185,129,0.12) 0%, transparent 70%)' : 'radial-gradient(ellipse, rgba(5,150,105,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{ maxWidth: '780px', position: 'relative' }}>

          {/* Badge */}
          <div className="anim-fade-up" style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '6px 16px', borderRadius: '99px',
            background: T.accentBg,
            border: `1px solid ${T.accent}33`,
            fontSize: '13px', fontWeight: 600,
            color: T.accentLight,
            marginBottom: '28px',
          }}>
            <Star size={13} fill={T.accentLight} color={T.accentLight} />
            AI Meeting Intelligence Platform
          </div>

          {/* Headline */}
          <h1
            className="anim-fade-up anim-fade-up-1"
            style={{
              fontSize: 'clamp(36px, 6vw, 68px)',
              fontWeight: 900,
              letterSpacing: '-0.05em',
              lineHeight: 1.1,
              color: T.text,
              margin: '0 0 24px',
            }}
          >
            Transform Meetings Into
            <br />
            <span className="gradient-text">
              Actionable Intelligence
            </span>
          </h1>

          {/* Subtitle */}
          <p
            className="anim-fade-up anim-fade-up-2"
            style={{
              fontSize: '18px', fontWeight: 400,
              color: T.text3, lineHeight: 1.7,
              margin: '0 0 40px',
              maxWidth: '560px', marginLeft: 'auto', marginRight: 'auto',
            }}
          >
            Upload any meeting recording. Get AI summaries, decisions,
            action items and a searchable knowledge base — in minutes.
          </p>

          {/* CTAs */}
          <div
            className="anim-fade-up anim-fade-up-3"
            style={{
              display: 'flex', gap: '12px',
              justifyContent: 'center', flexWrap: 'wrap',
            }}
          >
            {isAuthenticated ? (
              <button
                onClick={() => navigate('/app')}
                style={{
                  padding: '14px 32px', borderRadius: '12px',
                  background: T.btnGrad, border: 'none',
                  color: '#fff', fontSize: '16px', fontWeight: 700,
                  cursor: 'pointer', boxShadow: T.btnShadow,
                  display: 'flex', alignItems: 'center', gap: '8px',
                  transition: 'all 0.15s ease', fontFamily: 'var(--font)',
                }}
                onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseLeave={e => e.currentTarget.style.transform = 'none'}
              >
                Go to Dashboard <ArrowRight size={18} />
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate('/register')}
                  style={{
                    padding: '14px 32px', borderRadius: '12px',
                    background: isDark ? '#10b981' : '#059669',
                  border: 'none',
                    color: '#fff', fontSize: '16px', fontWeight: 700,
                    cursor: 'pointer',
                    boxShadow: '0 4px 20px rgba(16,185,129,0.32)',
                    display: 'flex', alignItems: 'center', gap: '8px',
                    transition: 'all 0.15s ease', fontFamily: 'var(--font)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 28px rgba(16,185,129,0.44)' }}
                  onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(16,185,129,0.32)' }}
                >
                  Get Started Free <ArrowRight size={18} />
                </button>
                <button
                  onClick={() => navigate('/demo')}
                  style={{
                    padding: '14px 28px', borderRadius: '12px',
                    background: T.surface,
                    border: `1px solid ${T.border}`,
                    color: T.text2, fontSize: '16px', fontWeight: 600,
                    cursor: 'pointer', boxShadow: T.cardShadow,
                    display: 'flex', alignItems: 'center', gap: '8px',
                    transition: 'all 0.15s ease', fontFamily: 'var(--font)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = T.accent
                    e.currentTarget.style.transform = 'translateY(-2px)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = T.border
                    e.currentTarget.style.transform = 'none'
                  }}
                >
                  <Play size={17} /> Try Demo
                </button>
              </>
            )}
          </div>

          {/* Social proof */}
          <div
            className="anim-fade-up anim-fade-up-4"
            style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'center', gap: '24px',
              marginTop: '48px', flexWrap: 'wrap',
            }}
          >
            {[
              { icon: <Clock size={15} />,    text: 'Setup in 2 minutes'    },
              { icon: <Shield size={15} />,   text: 'Private & secure'      },
              { icon: <Lock size={15} />,     text: 'Free forever'          },
            ].map(item => (
              <div key={item.text} style={{
                display: 'flex', alignItems: 'center', gap: '7px',
                fontSize: '13.5px', fontWeight: 500, color: T.text3,
              }}>
                <span style={{ color: T.accentLight }}>{item.icon}</span>
                {item.text}
              </div>
            ))}
          </div>

          {/* Stats */}
          <div
            className="anim-fade-up anim-fade-up-5"
            style={{
              display: 'flex', justifyContent: 'center',
              gap: '48px', marginTop: '64px',
              flexWrap: 'wrap',
            }}
          >
            {[
            { value: 10,  suffix: '+',  label: 'File Formats Supported' },
            { value: 4,   suffix: '',   label: 'AI Agents Working'      },
            { value: 100, suffix: '%',  label: 'Free Forever'           },
          ].map(s => (
                <div
                    key={s.label}
                    style={{
                    textAlign: 'center',
                    padding: '0 12px',
                    }}
                >
                    <div
                    className="gradient-text"
                    style={{
                        fontSize: '42px',
                        fontWeight: 900,
                        letterSpacing: '-0.06em',
                        lineHeight: 0.95,
                    }}
                    >
                    <Counter
                        target={s.value}
                        suffix={s.suffix}
                    />
                    </div>

                    <div
                    style={{
                        fontSize: '12px',
                        color: T.text3,
                        fontWeight: 600,
                        marginTop: '8px',
                        letterSpacing: '0.02em',
                        textTransform: 'uppercase',
                    }}
                    >
                    {s.label}
                    </div>
                </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────────────── */}
      <section id="features" style={{
        padding: '100px 32px',
        background: isDark ? T.surface : T.surface2,
      }}>
        <div style={{ maxWidth: '1100px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <div style={{
              fontSize: '13px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: T.accentLight, marginBottom: '12px',
            }}>
              Everything you need
            </div>
            <h2 style={{
              fontSize: 'clamp(28px, 4vw, 42px)',
              fontWeight: 800, letterSpacing: '-0.04em',
              color: T.text, margin: 0,
            }}>
              Meeting intelligence, fully automated
            </h2>
            <p style={{
              fontSize: '17px', color: T.text3,
              marginTop: '14px', lineHeight: 1.6,
            }}>
              From raw recording to structured insights in minutes.
            </p>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
            gap: '20px',
          }}>
            {features.map(f => (
              <FeatureCard key={f.title} {...f} T={T} />
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────────────── */}
      <section id="demo" style={{ padding: '100px 32px' }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '60px' }}>
            <div style={{
              fontSize: '13px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: T.accentLight, marginBottom: '12px',
            }}>
              How it works
            </div>
            <h2 style={{
              fontSize: 'clamp(28px, 4vw, 42px)',
              fontWeight: 800, letterSpacing: '-0.04em',
              color: T.text, margin: 0,
            }}>
              Three steps to meeting clarity
            </h2>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '24px',
          }}>
            {[
              {
                step: '01',
                icon: <Upload size={24} color={T.blueText} />,
                bg: T.blueBg,
                title: 'Upload Recording',
                desc: 'Drop any audio, video file or paste a YouTube URL. We handle the rest.',
              },
              {
                step: '02',
                icon: <Zap size={24} color={T.purpleText} />,
                bg: T.purpleBg,
                title: 'AI Processes It',
                desc: 'Four specialized AI agents analyze your meeting in parallel — transcript, summary, decisions, actions.',
              },
              {
                step: '03',
                icon: <TrendingUp size={24} color={T.emeraldText} />,
                bg: T.emeraldBg,
                title: 'Get Intelligence',
                desc: 'Review a full structured report and chat with your meeting using AI.',
              },
            ].map((item, i) => (
              <div key={item.step} className="anim-fade-up" style={{ animationDelay: `${i * 0.08}s` }}>
                <div style={{
                  padding: '32px 28px',
                  background: T.surface,
                  border: `1px solid ${T.border}`,
                  borderRadius: '20px',
                  boxShadow: T.cardShadow,
                  height: '100%',
                }}>
                  <div style={{
                    fontSize: '13px', fontWeight: 800,
                    letterSpacing: '0.1em',
                    color: T.accentLight,
                    marginBottom: '16px',
                  }}>
                    STEP {item.step}
                  </div>
                  <div style={{
                    width: '48px', height: '48px',
                    borderRadius: '12px', background: item.bg,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginBottom: '18px',
                  }}>
                    {item.icon}
                  </div>
                  <div style={{
                    fontSize: '18px', fontWeight: 700,
                    color: T.text, letterSpacing: '-0.03em',
                    marginBottom: '10px',
                  }}>
                    {item.title}
                  </div>
                  <div style={{
                    fontSize: '14px', color: T.text3,
                    lineHeight: 1.65,
                  }}>
                    {item.desc}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Demo CTA */}
          <div style={{ textAlign: 'center', marginTop: '48px' }}>
            <button
              onClick={() => navigate('/demo')}
              style={{
                padding: '13px 32px', borderRadius: '12px',
                background: isDark ? '#10b981' : '#059669', border: 'none',
                color: '#fff', fontSize: '15px', fontWeight: 700,
                cursor: 'pointer', boxShadow: '0 4px 16px rgba(16,185,129,0.30)',
                display: 'inline-flex', alignItems: 'center', gap: '9px',
                transition: 'all 0.15s ease', fontFamily: 'var(--font)',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'none'}
            >
              <Play size={16} /> See Live Demo
            </button>
          </div>
        </div>
      </section>

      {/* ── WHY CREATE ACCOUNT ────────────────────────────────────────────────── */}
      <section style={{
        padding: '100px 32px',
        background: isDark ? T.surface : T.surface2,
      }}>
        <div style={{ maxWidth: '900px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{
            fontSize: '13px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: T.accentLight, marginBottom: '12px',
          }}>
            Free forever
          </div>
          <h2 style={{
            fontSize: 'clamp(28px, 4vw, 42px)',
            fontWeight: 800, letterSpacing: '-0.04em',
            color: T.text, margin: '0 0 16px',
          }}>
            Everything unlocked, no catch
          </h2>
          <p style={{
            fontSize: '17px', color: T.text3,
            marginBottom: '48px', lineHeight: 1.6,
          }}>
            Create a free account and unlock the complete Summly experience.
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '12px', marginBottom: '48px',
          }}>
            {benefits.map(b => (
              <div key={b.label} style={{
                padding: '18px 20px',
                background: T.surface,
                border: `1px solid ${T.border}`,
                borderRadius: '14px',
                display: 'flex', alignItems: 'center', gap: '12px',
                boxShadow: T.cardShadow,
              }}>
                <span style={{ fontSize: '20px' }}>{b.icon}</span>
                <span style={{
                  fontSize: '14px', fontWeight: 600,
                  color: T.text,
                }}>
                  {b.label}
                </span>
              </div>
            ))}
          </div>

          {!isAuthenticated && (
            <button
              onClick={() => navigate('/register')}
              style={{
                padding: '15px 40px', borderRadius: '13px',
                background: isDark ? '#10b981' : '#059669', border: 'none',
                color: '#fff', fontSize: '17px', fontWeight: 700,
                cursor: 'pointer', boxShadow: '0 4px 20px rgba(16,185,129,0.32)',
                display: 'inline-flex', alignItems: 'center', gap: '9px',
                transition: 'all 0.15s ease', fontFamily: 'var(--font)',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'none'}
            >
              Create Free Account <ArrowRight size={18} />
            </button>
          )}
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────────────────────────────── */}
      <section id="faq" style={{ padding: '100px 32px' }}>
        <div style={{ maxWidth: '720px', margin: '0 auto' }}>
          <div style={{ textAlign: 'center', marginBottom: '56px' }}>
            <div style={{
              fontSize: '13px', fontWeight: 700,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              color: T.accentLight, marginBottom: '12px',
            }}>
              FAQ
            </div>
            <h2 style={{
              fontSize: 'clamp(26px, 4vw, 38px)',
              fontWeight: 800, letterSpacing: '-0.04em',
              color: T.text, margin: 0,
            }}>
              Frequently asked questions
            </h2>
          </div>

          <div style={{
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: '20px',
            padding: '8px 32px',
            boxShadow: T.cardShadow,
          }}>
            {faqs.map(f => (
              <FaqItem key={f.q} q={f.q} a={f.a} T={T} />
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER ────────────────────────────────────────────────────────────── */}
      <footer style={{
        padding: '48px 32px',
        borderTop: `1px solid ${T.border}`,
        background: isDark ? T.surface : T.surface2,
      }}>
        <div style={{
          maxWidth: '1100px', margin: '0 auto',
          display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap', gap: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: 30, height: 30, borderRadius: '8px',
              background: isDark ? '#1A1A1D' : '#EBEBEA',
              border: `1px solid ${isDark ? '#2A2A2E' : '#D8D8D4'}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{
                fontSize: '14px', fontWeight: 800,
                color: isDark ? '#10b981' : '#059669',
                letterSpacing: '-0.06em', lineHeight: 1,
                fontFamily: 'Inter, sans-serif',
              }}>S</span>
            </div>
            <span style={{
              fontSize: '16px', fontWeight: 800,
              letterSpacing: '-0.05em', color: T.text,
              fontFamily: 'Inter, sans-serif',
            }}>
              Summly
            </span>
          </div>

          <div style={{
            display: 'flex', gap: '24px', flexWrap: 'wrap',
          }}>
            {[
              { label: 'Features', href: '#features' },
              { label: 'Demo',     href: '/demo'     },
              { label: 'Creator',  href: '/creator'  },
              { label: 'Support',  href: '/support'  },
              { label: 'Sign In',  href: '/login'    },
              { label: 'Register', href: '/register' },
            ].map(l => (
                
              <a key={l.label} href={l.href} style={{
                fontSize: '14px', color: T.text3,
                fontWeight: 500, textDecoration: 'none',
                transition: 'color 0.15s ease',
              }}
                onMouseEnter={e => e.currentTarget.style.color = T.text}
                onMouseLeave={e => e.currentTarget.style.color = T.text3}
              >
                {l.label}
              </a>
            ))}
          </div>

          <div style={{ fontSize: '13px', color: T.text4 }}>
            Built by Pankaj Thakur — &copy; {new Date().getFullYear()}
          </div>
        </div>
      </footer>
    </div>
  )
}