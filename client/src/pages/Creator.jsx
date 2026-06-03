// client/src/pages/Creator.jsx

import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  GitFork,      
  Users,
  Mail,
  Globe,
  ArrowRight,
  Code2,
  Brain,
  Database,
  Layers,
  Terminal,
  Cpu,
  ExternalLink,
  Mic,
} from 'lucide-react'

import { useTheme } from '../ThemeContext'
import Navbar from '../components/Navbar'

// ── Animated text reveal ───────────────────────────────────────────────────────
function AnimatedName() {
  const { T } = useTheme()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(t)
  }, [])

  const letters = 'PANKAJ THAKUR'.split('')

  return (
    <div style={{
      fontSize: 'clamp(48px, 7vw, 88px)',
      fontWeight: 900,
      letterSpacing: '-0.05em',
      lineHeight: 0.95,
      display: 'flex', flexWrap: 'wrap',
      justifyContent: 'center',
      gap: '0px',
    }}>
      {letters.map((l, i) => (
        <span
          key={i}
          style={{
            display: 'inline-block',
            opacity: visible ? 1 : 0,
            transform: visible ? 'translateY(0)' : 'translateY(40px)',
            transition: `opacity 0.5s ease ${i * 0.04}s, transform 0.5s ease ${i * 0.04}s`,
            color: l === ' ' ? 'transparent' : T.text,
            width: l === ' ' ? '0.22em' : 'auto',
            textShadow: visible && l !== ' ' ? `0 0 80px ${T.accent}33` : 'none',
          }}
        >
          {l === ' ' ? '\u00A0' : l}
        </span>
      ))}
    </div>
  )
}

// ── Badge ──────────────────────────────────────────────────────────────────────
function Badge({ icon, label, color, bg }) {
  const { T } = useTheme()
  const [hov, setHov] = useState(false)
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: '8px',
        padding: '9px 16px', borderRadius: '99px',
        background: hov ? color + '22' : bg,
        border: `1px solid ${hov ? color + '66' : color + '33'}`,
        transition: 'all 0.18s ease',
        transform: hov ? 'translateY(-2px)' : 'none',
        cursor: 'default',
      }}
    >
      <span style={{ color, display: 'flex', alignItems: 'center' }}>{icon}</span>
      <span style={{
        fontSize: '13px', fontWeight: 650,
        color: hov ? color : T.text2,
        letterSpacing: '-0.01em',
      }}>
        {label}
      </span>
    </div>
  )
}

// ── Timeline item ──────────────────────────────────────────────────────────────
function TimelineItem({ year, title, desc, accent, isLast, T }) {
  const [vis, setVis] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVis(true) },
      { threshold: 0.3 }
    )
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [])

  return (
    <div ref={ref} style={{
      display: 'flex', gap: '24px',
      opacity: vis ? 1 : 0,
      transform: vis ? 'none' : 'translateX(-20px)',
      transition: 'all 0.5s ease',
    }}>
      <div style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', flexShrink: 0,
      }}>
        <div style={{
          width: '14px', height: '14px', borderRadius: '50%',
          background: accent,
          boxShadow: `0 0 12px ${accent}66`,
          flexShrink: 0, marginTop: '4px',
        }} />
        {!isLast && (
          <div style={{
            width: '2px', flex: 1,
            background: `linear-gradient(to bottom, ${accent}44, transparent)`,
            marginTop: '6px', minHeight: '40px',
          }} />
        )}
      </div>
      <div style={{ paddingBottom: isLast ? 0 : '32px' }}>
        <div style={{
          fontSize: '12px', fontWeight: 700,
          color: accent, letterSpacing: '0.08em',
          textTransform: 'uppercase', marginBottom: '4px',
        }}>
          {year}
        </div>
        <div style={{
          fontSize: '17px', fontWeight: 700,
          color: T.text, letterSpacing: '-0.02em',
          marginBottom: '6px',
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
    </div>
  )
}

// ── Social link ────────────────────────────────────────────────────────────────
function SocialLink({ icon, label, href, color, T }) {
  const [hov, setHov] = useState(false)
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        padding: '14px 20px', borderRadius: '14px',
        background: hov ? color + '12' : T.surface,
        border: `1px solid ${hov ? color + '44' : T.border}`,
        textDecoration: 'none',
        transition: 'all 0.18s ease',
        transform: hov ? 'translateY(-2px)' : 'none',
        boxShadow: hov ? `0 8px 24px ${color}18` : T.cardShadow,
      }}
    >
      <div style={{
        width: '38px', height: '38px', borderRadius: '10px',
        background: color + '18',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <span style={{ color }}>{icon}</span>
      </div>
      <div>
        <div style={{
          fontSize: '14px', fontWeight: 650,
          color: T.text, letterSpacing: '-0.01em',
        }}>
          {label}
        </div>
      </div>
      <ExternalLink
        size={14} color={T.text4}
        style={{ marginLeft: 'auto', opacity: hov ? 1 : 0, transition: 'opacity 0.15s ease' }}
      />
    </a>
  )
}

// ── Project card ───────────────────────────────────────────────────────────────
function ProjectCard({ title, desc, tags, icon, color, bg, T }) {
  const [hov, setHov] = useState(false)
  return (
    <div
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        padding: '28px',
        borderRadius: '18px',
        background: T.surface,
        border: `1px solid ${hov ? color + '44' : T.border}`,
        boxShadow: hov ? `0 12px 40px ${color}14` : T.cardShadow,
        transition: 'all 0.2s ease',
        transform: hov ? 'translateY(-3px)' : 'none',
      }}
    >
      <div style={{
        width: '48px', height: '48px', borderRadius: '13px',
        background: bg, marginBottom: '18px',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '22px',
      }}>
        {icon}
      </div>
      <div style={{
        fontSize: '18px', fontWeight: 750,
        color: T.text, letterSpacing: '-0.03em',
        marginBottom: '8px',
      }}>
        {title}
      </div>
      <div style={{
        fontSize: '14px', color: T.text3,
        lineHeight: 1.65, marginBottom: '18px',
      }}>
        {desc}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {tags.map(tag => (
          <span key={tag} style={{
            padding: '3px 10px', borderRadius: '99px',
            fontSize: '11.5px', fontWeight: 600,
            color, background: bg,
            border: `1px solid ${color}22`,
          }}>
            {tag}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Main ───────────────────────────────────────────────────────────────────────
export default function Creator() {
  const { T, isDark } = useTheme()
  const navigate = useNavigate()

  const GITHUB_URL    = 'https://github.com/pankaj0160'
  const LINKEDIN_URL  = 'https://www.linkedin.com/in/pankaj-thakur-b3b749288/'
  const PORTFOLIO_URL = 'https://pankaj-portfolio-blue.vercel.app/'
  const EMAIL         = 'pankajthakur.dev01@gmail.com'

  const badges = [
    { icon: <Brain size={15} />,    label: 'AI Engineer',          color: T.accent,  bg: T.accentBg  },
    { icon: <Code2 size={15} />,    label: 'Full Stack Developer',  color: T.blue,    bg: T.blueBg    },
    { icon: <Terminal size={15} />, label: 'FastAPI Developer',     color: T.emerald, bg: T.emeraldBg },
    { icon: <Database size={15} />, label: 'RAG Developer',         color: T.purple,  bg: T.purpleBg  },
    { icon: <Layers size={15} />,   label: 'Open Source Builder',   color: T.orange,  bg: T.orangeBg  },
    { icon: <Cpu size={15} />,      label: 'LLM Engineer',          color: T.cyan,    bg: T.cyanBg    },
  ]

  const timeline = [
    {
      year: '2026',
      title: 'Built Summly',
      desc: 'Designed and built Summly — an AI Meeting Intelligence Platform with RAG, LangGraph agents, ChromaDB, and a premium React frontend.',
      accent: T.accent,
    },
    {
      year: '2026+',
      title: 'AI Engineering Journey',
      desc: 'Continuing to build production-grade AI systems. Focused on RAG architectures, LLM applications, and AI-powered SaaS products.',
      accent: T.orange,
    },
  ]

  const skills = [
    { category: 'AI & ML',  items: ['LangChain', 'LangGraph', 'RAG', 'ChromaDB', 'Whisper', 'LLaMA', 'Groq'] },
    { category: 'Backend',  items: ['Python', 'FastAPI', 'SQLite', 'PostgreSQL', 'REST APIs', 'WebSockets'] },
    { category: 'Frontend', items: ['React', 'JavaScript', 'Tailwind CSS', 'Vite', 'Streamlit'] },
  ]

  const socials = [
    {
      icon: <GitFork size={20} />,
      label: 'GitHub — pankaj0160',
      href: GITHUB_URL,
      color: T.text2,
    },
    {
      icon: <Users size={20} />,
      label: 'LinkedIn',
      href: LINKEDIN_URL,
      color: '#0077b5',
    },
    {
      icon: <Globe size={20} />,
      label: 'Portfolio',
      href: PORTFOLIO_URL,
      color: T.accent,
    },
    {
      icon: <Mail size={20} />,
      label: EMAIL,
      href: `mailto:${EMAIL}`,
      color: T.emerald,
    },
  ]

  return (
    <div style={{ background: T.bg, minHeight: '100vh' }}>
      <Navbar />

      {/* ── HERO ─────────────────────────────────────────────────────────────── */}
      <section style={{
        minHeight: '100vh',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '120px 32px 80px',
        textAlign: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Background glows */}
        <div style={{
          position: 'absolute', top: '30%', left: '50%',
          transform: 'translateX(-50%)',
          width: '800px', height: '400px',
          background: `radial-gradient(ellipse, ${T.accent}14 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />
        <div style={{
          position: 'absolute', top: '20%', left: '15%',
          width: '300px', height: '300px',
          background: `radial-gradient(ellipse, ${T.purple}10 0%, transparent 70%)`,
          pointerEvents: 'none',
        }} />

        <div style={{ maxWidth: '860px', position: 'relative' }}>

          {/* Label */}
          <div className="anim-fade-up" style={{
            display: 'inline-flex', alignItems: 'center', gap: '8px',
            padding: '6px 16px', borderRadius: '99px',
            background: T.accentBg, border: `1px solid ${T.accent}33`,
            fontSize: '13px', fontWeight: 600, color: T.accentLight,
            marginBottom: '36px',
          }}>
            <Mic size={13} />
            Creator of Summly
          </div>

          {/* Name */}
          <div className="anim-fade-up anim-fade-up-1" style={{ marginBottom: '28px' }}>
            <AnimatedName />
          </div>

          {/* Title */}
          <div className="anim-fade-up anim-fade-up-2" style={{
            fontSize: 'clamp(18px, 3vw, 26px)',
            fontWeight: 400, color: T.text3,
            lineHeight: 1.5, marginBottom: '32px',
          }}>
            AI Engineer · Full Stack Developer 
          </div>

          {/* Bio */}
          <p className="anim-fade-up anim-fade-up-3" style={{
            fontSize: '17px', color: T.text2,
            lineHeight: 1.8, fontWeight: 400,
            maxWidth: '600px', margin: '0 auto 40px',
          }}>
            Building intelligent software that transforms ideas into real-world impact.
          </p>

          {/* Badges */}
          <div className="anim-fade-up anim-fade-up-4" style={{
            display: 'flex', flexWrap: 'wrap',
            justifyContent: 'center', gap: '8px',
            marginBottom: '48px',
          }}>
            {badges.map(b => (
              <Badge key={b.label} {...b} />
            ))}
          </div>

          {/* CTAs */}
          <div className="anim-fade-up anim-fade-up-5" style={{
            display: 'flex', gap: '12px',
            justifyContent: 'center', flexWrap: 'wrap',
          }}>
            <button
              onClick={() => navigate('/register')}
              style={{
                padding: '13px 28px', borderRadius: '12px',
                background: T.btnGrad, border: 'none',
                color: '#fff', fontSize: '15px', fontWeight: 700,
                cursor: 'pointer', boxShadow: T.btnShadow,
                display: 'inline-flex', alignItems: 'center', gap: '8px',
                transition: 'all 0.15s ease', fontFamily: 'var(--font-body)',
              }}
              onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={e => e.currentTarget.style.transform = 'none'}
            >
              Try Summly Free <ArrowRight size={16} />
            </button>
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                padding: '13px 28px', borderRadius: '12px',
                background: T.surface,
                border: `1px solid ${T.border}`,
                color: T.text2, fontSize: '15px', fontWeight: 600,
                cursor: 'pointer', boxShadow: T.cardShadow,
                display: 'inline-flex', alignItems: 'center', gap: '8px',
                transition: 'all 0.15s ease',
                textDecoration: 'none',
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
              <GitFork size={17} /> View GitHub
            </a>
          </div>
        </div>
      </section>

      {/* ── ABOUT ────────────────────────────────────────────────────────────── */}
      <section style={{
        padding: '100px 32px',
        background: isDark ? T.surface : T.surface2,
      }}>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            gap: '60px', alignItems: 'center',
          }}>

            {/* Left — story */}
            <div>
              <div style={{
                fontSize: '13px', fontWeight: 700,
                letterSpacing: '0.12em', textTransform: 'uppercase',
                color: T.accentLight, marginBottom: '12px',
              }}>
                About me
              </div>
              <h2 style={{
                fontSize: 'clamp(26px, 4vw, 36px)',
                fontWeight: 800, letterSpacing: '-0.04em',
                color: T.text, margin: '0 0 20px',
              }}>
                Building at the intersection of AI and product
              </h2>
              <p style={{
                fontSize: '15px', color: T.text3,
                lineHeight: 1.8, marginBottom: '16px',
              }}>
                I'm Pankaj Thakur, an AI engineer and full-stack developer
                focused on building production-grade AI applications. I specialize
                in RAG architectures, LLM integration, and AI-powered SaaS products.
              </p>
              <p style={{
                fontSize: '15px', color: T.text3,
                lineHeight: 1.8, marginBottom: '24px',
              }}>
                Summly is my latest project — an AI Meeting Intelligence Platform
                that I designed and built from scratch, combining Whisper transcription,
                LangGraph agents, ChromaDB RAG, and a premium React frontend.
              </p>
              <div style={{
                display: 'flex', gap: '12px', flexWrap: 'wrap',
              }}>
                <a
                  href={PORTFOLIO_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    fontSize: '13px', color: T.accentLight, fontWeight: 600,
                    textDecoration: 'none',
                    padding: '6px 14px', borderRadius: '8px',
                    background: T.accentBg, border: `1px solid ${T.accent}33`,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Globe size={13} /> View Portfolio
                </a>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  fontSize: '14px', color: T.emerald, fontWeight: 600,
                }}>
                  <div style={{
                    width: '8px', height: '8px', borderRadius: '50%',
                    background: T.emerald,
                    boxShadow: `0 0 8px ${T.emerald}`,
                  }} />
                  Open to opportunities
                </div>
              </div>
            </div>

            {/* Right — skills */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {skills.map(s => (
                <div key={s.category} style={{
                  padding: '18px 20px',
                  background: T.surface,
                  border: `1px solid ${T.border}`,
                  borderRadius: '14px',
                  boxShadow: T.cardShadow,
                }}>
                  <div style={{
                    fontSize: '11px', fontWeight: 700,
                    letterSpacing: '0.1em', textTransform: 'uppercase',
                    color: T.text3, marginBottom: '10px',
                  }}>
                    {s.category}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {s.items.map(item => (
                      <span key={item} style={{
                        padding: '4px 10px', borderRadius: '99px',
                        fontSize: '12px', fontWeight: 600,
                        color: T.text2, background: T.surface2,
                        border: `1px solid ${T.border}`,
                      }}>
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>


      {/* ── CONNECT ──────────────────────────────────────────────────────────── */}
      <section style={{ padding: '100px 32px' }}>
        <div style={{ maxWidth: '640px', margin: '0 auto', textAlign: 'center' }}>
          <div style={{
            fontSize: '13px', fontWeight: 700,
            letterSpacing: '0.12em', textTransform: 'uppercase',
            color: T.accentLight, marginBottom: '12px',
          }}>
            Get in touch
          </div>
          <h2 style={{
            fontSize: 'clamp(26px, 4vw, 38px)',
            fontWeight: 800, letterSpacing: '-0.04em',
            color: T.text, margin: '0 0 16px',
          }}>
            Let's connect
          </h2>
          <p style={{
            fontSize: '16px', color: T.text3,
            marginBottom: '40px', lineHeight: 1.65,
          }}>
            I'm always open to interesting projects, collaborations,
            and conversations about AI and product development.
          </p>

          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            gap: '12px',
          }}>
            {socials.map(s => (
              <SocialLink key={s.label} {...s} T={T} />
            ))}
          </div>
        </div>
      </section>

      {/* ── FOOTER CTA ───────────────────────────────────────────────────────── */}
      <section style={{
        padding: '80px 32px',
        background: isDark ? T.surface : T.surface2,
        textAlign: 'center',
        borderTop: `1px solid ${T.border}`,
      }}>
        <div style={{ maxWidth: '600px', margin: '0 auto' }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '16px',
            background: T.btnGrad, boxShadow: T.btnShadow,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 20px',
          }}>
            <Mic size={26} color="#fff" strokeWidth={2.5} />
          </div>
          <h2 style={{
            fontSize: '28px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            margin: '0 0 12px',
          }}>
            Try Summly
          </h2>
          <p style={{
            fontSize: '16px', color: T.text3,
            marginBottom: '28px', lineHeight: 1.6,
          }}>
            The AI meeting platform I built. Free forever.
          </p>
          <button
            onClick={() => navigate('/register')}
            style={{
              padding: '13px 32px', borderRadius: '12px',
              background: T.btnGrad, border: 'none',
              color: '#fff', fontSize: '15px', fontWeight: 700,
              cursor: 'pointer', boxShadow: T.btnShadow,
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              transition: 'all 0.15s ease', fontFamily: 'var(--font-body)',
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'none'}
          >
            Get Started Free <ArrowRight size={16} />
          </button>
        </div>
      </section>
    </div>
  )
}