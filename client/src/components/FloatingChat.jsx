// client/src/components/FloatingChat.jsx

import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../ThemeContext'
import { MessageSquare, X, Send, Bot, User, Sparkles } from 'lucide-react'
import { getMeetings, chatAcrossMeetings, chatWithMeeting } from '../api/client'
import { useLocation } from 'react-router-dom'

// Extract meeting ID from URL if on meeting detail page
function useMeetingIdFromUrl() {
  const loc = useLocation()
  const match = loc.pathname.match(/^\/meetings\/(\d+)$/)
  return match ? Number(match[1]) : null
}

const QUICK = [
  'What decisions were made?',
  'List all action items.',
  'Summarize recent meetings.',
]

export default function FloatingChat() {
  const { T }       = useTheme()
  const meetingId   = useMeetingIdFromUrl()

  const [open,     setOpen]     = useState(false)
  const [messages, setMessages] = useState([])
  const [input,    setInput]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const [pulse,    setPulse]    = useState(false)

  const bottomRef = useRef()
  const inputRef  = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Pulse the button after 3s to draw attention if never opened
  useEffect(() => {
    const t = setTimeout(() => setPulse(true), 3000)
    return () => clearTimeout(t)
  }, [])

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || loading) return

    setMessages(m => [...m, { role: 'user', content: q }])
    setInput('')
    setLoading(true)

    try {
      const res = meetingId
        ? await chatWithMeeting(q, meetingId)
        : await chatAcrossMeetings(q)

      setMessages(m => [...m, {
        role:    'assistant',
        content: res.answer,
        sources: res.sources || [],
      }])
    } catch (e) {
      setMessages(m => [...m, {
        role:    'assistant',
        content: `⚠️ ${e.message || 'Error'}`,
        sources: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* ── Chat window ── */}
      {open && (
        <div
          className="anim-fade-up"
          style={{
            position: 'fixed',
            bottom: '88px', right: '28px',
            width: '380px', height: '520px',
            background: T.surface,
            border: `1px solid ${T.border}`,
            borderRadius: '20px',
            boxShadow: '0 24px 64px rgba(0,0,0,0.3)',
            display: 'flex', flexDirection: 'column',
            overflow: 'hidden',
            zIndex: 998,
          }}
        >
          {/* Header */}
          <div style={{
            padding: '16px 18px',
            borderBottom: `1px solid ${T.border}`,
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between',
            background: T.surface,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '30px', height: '30px', borderRadius: '8px',
                background: T.btnGrad,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Bot size={15} color="#fff" />
              </div>
              <div>
                <div style={{
                  fontSize: '14px', fontWeight: 700,
                  color: T.text, letterSpacing: '-0.02em',
                }}>
                  Summly AI
                </div>
                <div style={{ fontSize: '11px', color: T.text3 }}>
                  {meetingId
                    ? `Chatting with Meeting #${meetingId}`
                    : 'Searching all meetings'
                  }
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: T.surface2,
                border: `1px solid ${T.border}`,
                borderRadius: '7px',
                width: '28px', height: '28px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: T.text3,
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.color = T.text}
              onMouseLeave={e => e.currentTarget.style.color = T.text3}
            >
              <X size={13} />
            </button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: 'auto',
            padding: '14px',
            display: 'flex', flexDirection: 'column',
            gap: '12px',
          }}>
            {messages.length === 0 ? (
              <div style={{
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                height: '100%', textAlign: 'center', padding: '16px',
              }}>
                <div style={{
                  width: '44px', height: '44px', borderRadius: '12px',
                  background: T.accentBg, marginBottom: '12px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Sparkles size={20} color={T.accentLight} />
                </div>
                <div style={{
                  fontSize: '15px', fontWeight: 700,
                  color: T.text, marginBottom: '6px',
                  letterSpacing: '-0.02em',
                }}>
                  Ask Summly AI
                </div>
                <div style={{
                  fontSize: '12.5px', color: T.text3,
                  marginBottom: '18px', lineHeight: 1.5,
                }}>
                  {meetingId
                    ? 'Ask about this meeting'
                    : 'Ask about any of your meetings'
                  }
                </div>
                {/* Quick questions */}
                <div style={{
                  display: 'flex', flexDirection: 'column',
                  gap: '6px', width: '100%',
                }}>
                  {QUICK.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => send(q)}
                      style={{
                        padding: '9px 12px',
                        borderRadius: '9px',
                        background: T.surface2,
                        border: `1px solid ${T.border}`,
                        color: T.text2, fontSize: '12.5px',
                        fontWeight: 500, cursor: 'pointer',
                        textAlign: 'left', fontFamily: 'var(--font)',
                        transition: 'all 0.15s ease',
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = T.accent
                        e.currentTarget.style.color = T.text
                        e.currentTarget.style.background = T.accentBg
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = T.border
                        e.currentTarget.style.color = T.text2
                        e.currentTarget.style.background = T.surface2
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((msg, i) => {
                  const isUser = msg.role === 'user'
                  return (
                    <div key={i} style={{
                      display: 'flex',
                      justifyContent: isUser ? 'flex-end' : 'flex-start',
                      gap: '7px', alignItems: 'flex-start',
                    }}>
                      {!isUser && (
                        <div style={{
                          width: '24px', height: '24px', borderRadius: '6px',
                          background: T.accentBg, flexShrink: 0,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          marginTop: '2px',
                        }}>
                          <Bot size={12} color={T.accentLight} />
                        </div>
                      )}
                      <div style={{
                        maxWidth: '82%',
                        padding: '9px 13px',
                        borderRadius: isUser
                          ? '14px 14px 4px 14px'
                          : '14px 14px 14px 4px',
                        background:  isUser ? T.btnGrad  : T.surface2,
                        border:      isUser ? 'none'     : `1px solid ${T.border}`,
                        fontSize:    '13px', color: isUser ? '#fff' : T.text2,
                        lineHeight:  1.65,
                        boxShadow:   isUser ? T.btnShadow : 'none',
                        whiteSpace:  'pre-wrap',
                      }}>
                        {msg.content}
                      </div>
                      {isUser && (
                        <div style={{
                          width: '24px', height: '24px', borderRadius: '6px',
                          background: T.surface3, flexShrink: 0,
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          marginTop: '2px',
                        }}>
                          <User size={12} color={T.text3} />
                        </div>
                      )}
                    </div>
                  )
                })}
                {loading && (
                  <div style={{ display: 'flex', gap: '7px', alignItems: 'center' }}>
                    <div style={{
                      width: '24px', height: '24px', borderRadius: '6px',
                      background: T.accentBg,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <Bot size={12} color={T.accentLight} />
                    </div>
                    <div style={{
                      padding: '9px 13px',
                      borderRadius: '14px 14px 14px 4px',
                      background: T.surface2,
                      border: `1px solid ${T.border}`,
                      display: 'flex', gap: '4px', alignItems: 'center',
                    }}>
                      {[0, 0.2, 0.4].map((d, i) => (
                        <div key={i} style={{
                          width: '5px', height: '5px', borderRadius: '50%',
                          background: T.text3,
                          animation: `fadeIn 0.9s ${d}s infinite alternate`,
                        }} />
                      ))}
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </>
            )}
          </div>

          {/* Input */}
          <div style={{
            padding: '12px 14px',
            borderTop: `1px solid ${T.border}`,
            display: 'flex', gap: '8px', alignItems: 'center',
          }}>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault(); send()
                }
              }}
              placeholder="Ask anything..."
              style={{
                flex: 1, padding: '9px 13px',
                borderRadius: '9px',
                border: `1px solid ${T.inputBorder}`,
                background: T.inputBg, color: T.text,
                fontSize: '13px', outline: 'none',
                fontFamily: 'var(--font)',
                transition: 'border-color 0.15s ease',
              }}
              onFocus={e => e.target.style.borderColor = T.borderFocus}
              onBlur={e => e.target.style.borderColor = T.inputBorder}
            />
            <button
              onClick={() => send()}
              disabled={!input.trim() || loading}
              style={{
                width: '34px', height: '34px',
                borderRadius: '9px',
                background: input.trim() && !loading ? T.btnGrad : T.surface2,
                border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.15s ease',
                boxShadow: input.trim() ? T.btnShadow : 'none',
                flexShrink: 0,
              }}
            >
              <Send size={14} color={input.trim() && !loading ? '#fff' : T.text4} />
            </button>
          </div>
        </div>
      )}

      {/* ── Floating button ── */}
      <button
        onClick={() => { setOpen(o => !o); setPulse(false) }}
        style={{
          position: 'fixed',
          bottom: '28px', right: '28px',
          width: '52px', height: '52px',
          borderRadius: '16px',
          background: open ? T.surface2 : T.btnGrad,
          border: open ? `1px solid ${T.border}` : 'none',
          boxShadow: open ? T.cardShadow : T.btnShadow,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 999,
          transition: 'all 0.2s ease',
          outline: 'none',
        }}
        onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.08)'}
        onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
      >
        {open
          ? <X size={20} color={T.text2} />
          : <MessageSquare size={20} color="#fff" />
        }
        {/* Pulse ring */}
        {pulse && !open && (
          <span style={{
            position: 'absolute', inset: '-4px',
            borderRadius: '20px',
            border: `2px solid ${T.accent}`,
            animation: 'fadeIn 1.5s infinite alternate',
            pointerEvents: 'none',
          }} />
        )}
      </button>
    </>
  )
}