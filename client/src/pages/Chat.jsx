// client/src/pages/Chat.jsx

import { useState, useRef, useEffect } from 'react'
import { useTheme } from '../ThemeContext'
import { useSearchParams } from 'react-router-dom'
import { getMeetings, chatWithMeeting, chatAcrossMeetings } from '../api/client'
import { PageHeader, Card, Button, EmptyState } from '../components/ui'
import { useScreenSize } from '../hooks/useScreenSize'
import {
  Send, Bot, User, ChevronDown,
  Globe, Mic, Sparkles, BookOpen,
  X, ChevronRight, SlidersHorizontal, Trash2,
} from 'lucide-react'

// ── Suggested questions ────────────────────────────────────────────────────────
const SUGGESTIONS_SINGLE = [
  'What decisions were made in this meeting?',
  'What are the key action items?',
  'Who is responsible for what?',
  'Summarize the main topics discussed.',
  'What were the deadlines mentioned?',
  'Were there any unresolved issues?',
]

const SUGGESTIONS_CROSS = [
  'What decisions have been made across all meetings?',
  'Show me all pending action items.',
  'What topics come up most often?',
  'Which meetings had the most decisions?',
  'Find all tasks assigned to specific people.',
  'What were the most recent decisions made?',
]

// ── Typing indicator ───────────────────────────────────────────────────────────
function TypingIndicator({ T }) {
  return (
    <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
      <div style={{
        width: '30px', height: '30px', borderRadius: '8px',
        background: T.accentBg, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Bot size={15} color={T.accentLight} />
      </div>
      <div style={{
        padding: '12px 16px',
        borderRadius: '14px 14px 14px 4px',
        background: T.surface2,
        border: `1px solid ${T.border}`,
        display: 'flex', gap: '5px', alignItems: 'center',
      }}>
        {[0, 0.2, 0.4].map((delay, i) => (
          <div
            key={i}
            style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: T.text3,
              animation: `fadeIn 0.9s ${delay}s infinite alternate`,
            }}
          />
        ))}
      </div>
    </div>
  )
}

// ── Single message ─────────────────────────────────────────────────────────────
function ChatMessage({ msg, T, onShowSources }) {
  const isUser = msg.role === 'user'
  const hasSources = !isUser && msg.sources?.length > 0

  return (
    <div className="anim-fade-up" style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      gap: '10px', alignItems: 'flex-start',
    }}>
      {!isUser && (
        <div style={{
          width: '30px', height: '30px', borderRadius: '8px',
          background: T.accentBg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: '2px',
        }}>
          <Bot size={15} color={T.accentLight} />
        </div>
      )}

      <div style={{ maxWidth: '78%' }}>
        {/* Bubble */}
        <div style={{
          padding: '12px 16px',
          borderRadius: isUser
            ? '16px 16px 4px 16px'
            : '16px 16px 16px 4px',
          background:  isUser ? T.btnGrad  : T.surface2,
          border:      isUser ? 'none'     : `1px solid ${T.border}`,
          fontSize:    '14px', fontWeight: 400,
          color:       isUser ? '#fff'     : T.text2,
          lineHeight:  1.72,
          boxShadow:   isUser ? T.btnShadow : 'none',
          whiteSpace: 'pre-wrap',
        }}>
          {msg.content}
        </div>

        {/* Sources row */}
        {hasSources && (
          <div style={{
            display: 'flex', alignItems: 'center',
            gap: '8px', marginTop: '7px',
            flexWrap: 'wrap',
          }}>
            <button
              onClick={() => onShowSources(msg.sources)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: '5px',
                padding: '3px 10px', borderRadius: '99px',
                fontSize: '11.5px', fontWeight: 600,
                color: T.accentLight, background: T.accentBg,
                border: `1px solid ${T.accent}33`,
                cursor: 'pointer', transition: 'all 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.background = T.accentHover}
              onMouseLeave={e => e.currentTarget.style.background = T.accentBg}
            >
              <BookOpen size={10} />
              {msg.sources.length} source{msg.sources.length !== 1 ? 's' : ''}
              <ChevronRight size={10} />
            </button>
          </div>
        )}
      </div>

      {isUser && (
        <div style={{
          width: '30px', height: '30px', borderRadius: '8px',
          background: T.surface3, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: '2px',
        }}>
          <User size={15} color={T.text3} />
        </div>
      )}
    </div>
  )
}

// ── Sources panel ──────────────────────────────────────────────────────────────
// FIX: this used to be a permanently-inline flex sibling with a hard-coded
// `width: 300px`. On mobile that's most of the screen's width added onto an
// already-full chat column — the classic cause of a horizontal scrollbar.
// On mobile it now renders as a full-screen overlay (fixed, slides up from
// the bottom) instead of squeezing in beside the chat.
function SourcesPanel({ sources, onClose, T, isMobile }) {
  return (
    <div
      className={isMobile ? 'anim-fade-up' : 'anim-fade-in'}
      style={isMobile ? {
        position: 'fixed', inset: 0, zIndex: 400,
        background: T.surface,
        display: 'flex', flexDirection: 'column',
      } : {
        width: '300px', flexShrink: 0,
        background: T.surface,
        border: `1px solid ${T.border}`,
        borderRadius: '16px',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: T.cardShadow,
      }}
    >      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 18px',
        borderBottom: `1px solid ${T.border}`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <BookOpen size={15} color={T.accent} />
          <span style={{
            fontSize: '14px', fontWeight: 700,
            color: T.text, letterSpacing: '-0.02em',
          }}>
            Sources
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none', border: 'none',
            cursor: 'pointer', color: T.text3,
            display: 'flex', alignItems: 'center',
            padding: '2px', borderRadius: '5px',
            transition: 'color 0.15s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.color = T.text}
          onMouseLeave={e => e.currentTarget.style.color = T.text3}
        >
          <X size={15} />
        </button>
      </div>

      {/* Source list */}
      <div style={{
        flex: 1, overflowY: 'auto',
        padding: '12px',
        display: 'flex', flexDirection: 'column', gap: '10px',
      }}>
        {sources.map((s, i) => (
          <div key={i} style={{
            padding: '13px 14px',
            borderRadius: '10px',
            background: T.surface2,
            border: `1px solid ${T.border}`,
          }}>
            {/* Source meta */}
            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px',
            }}>
              <span style={{
                fontSize: '11px', fontWeight: 700,
                letterSpacing: '0.06em', textTransform: 'uppercase',
                color: T.accentLight,
              }}>
                Meeting #{s.meeting_id}
              </span>
              <span style={{
                fontSize: '11px', fontWeight: 600,
                color: T.text3,
                background: T.surface3,
                padding: '2px 7px', borderRadius: '99px',
                border: `1px solid ${T.border}`,
              }}>
                {(s.score * 100).toFixed(0)}% match
              </span>
            </div>

            {/* Chunk text */}
            <p style={{
              fontSize: '12.5px', color: T.text2,
              lineHeight: 1.65, margin: 0,
              display: '-webkit-box',
              WebkitLineClamp: 4,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}>
              {s.text}
            </p>

            {/* Filename */}
            {s.filename && (
              <div style={{
                marginTop: '8px', fontSize: '11px',
                color: T.text4, fontWeight: 500,
              }}>
                📄 {s.filename}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Suggested questions ────────────────────────────────────────────────────────
function Suggestions({ suggestions, onSelect, T, isMobile }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: isMobile ? '28px 16px' : '40px 24px',
      flex: 1,
    }}>
      <div style={{
        width: '48px', height: '48px', borderRadius: '14px',
        background: T.accentBg,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: '16px',
      }}>
        <Sparkles size={22} color={T.accentLight} />
      </div>
      <div style={{
        fontSize: '18px', fontWeight: 700,
        letterSpacing: '-0.03em', color: T.text,
        marginBottom: '6px',
      }}>
        Ask anything
      </div>
      <div style={{
        fontSize: '13px', color: T.text3,
        marginBottom: '28px', textAlign: 'center',
      }}>
        Try one of these questions or type your own
      </div>
      <div style={{
        display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
        gap: '8px', width: '100%', maxWidth: '560px',
      }}>
        {suggestions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            style={{
              padding: '11px 14px',
              borderRadius: '10px',
              background: T.surface2,
              border: `1px solid ${T.border}`,
              color: T.text2, fontSize: '13px',
              fontWeight: 500, fontFamily: 'var(--font)',
              cursor: 'pointer', textAlign: 'left',
              lineHeight: 1.45,
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
  )
}

// ── Scope / Meeting filter controls ─────────────────────────────────────────────
// FIX: extracted from what used to be a permanent 224px-wide column so the
// exact same controls can be reused inside a mobile bottom-sheet instead of
// being duplicated (and inevitably drifting out of sync) between two places.
function FiltersPanel({
  mode, setMode, setSources, selId, setSelId, setMessages,
  loadingM, meetings, selectedMeeting, messages, T,
}) {
  return (
    <>
      {/* Mode */}
      <div style={{
        fontSize: '10px', fontWeight: 700,
        letterSpacing: '0.1em', textTransform: 'uppercase',
        color: T.text3, marginBottom: '8px',
      }}>
        Scope
      </div>
      <div style={{
        display: 'flex', flexDirection: 'column',
        gap: '5px', marginBottom: '20px',
      }}>
        {[
          { id: 'single', icon: <Mic size={13} />,   label: 'This Meeting'  },
          { id: 'cross',  icon: <Globe size={13} />, label: 'All Meetings'  },
        ].map(opt => (
          <button
            key={opt.id}
            onClick={() => { setMode(opt.id); setSources(null) }}
            style={{
              display: 'flex', alignItems: 'center', gap: '9px',
              padding: '9px 12px', borderRadius: '9px',
              fontSize: '13.5px',
              fontWeight: mode === opt.id ? 650 : 400,
              color: mode === opt.id ? T.navActiveText : T.text3,
              background: mode === opt.id ? T.navActiveBg : 'transparent',
              border: `1px solid ${mode === opt.id ? T.navActiveBorder : T.border}`,
              cursor: 'pointer', transition: 'all 0.15s ease',
              textAlign: 'left', width: '100%',
              fontFamily: 'var(--font)',
            }}
          >
            {opt.icon}
            {opt.label}
          </button>
        ))}
      </div>

      {/* Meeting selector */}
      {mode === 'single' && (
        <>
          <div style={{
            fontSize: '10px', fontWeight: 700,
            letterSpacing: '0.1em', textTransform: 'uppercase',
            color: T.text3, marginBottom: '8px',
          }}>
            Meeting
          </div>
          <div style={{ position: 'relative', marginBottom: '20px' }}>
            <select
              value={selId || ''}
              onChange={e => {
                setSelId(Number(e.target.value))
                setMessages([])
                setSources(null)
              }}
              style={{
                width: '100%',
                padding: '9px 32px 9px 12px',
                borderRadius: '9px',
                border: `1px solid ${T.inputBorder}`,
                background: T.inputBg,
                color: T.text,
                fontSize: '13px', fontWeight: 500,
                appearance: 'none', cursor: 'pointer',
                outline: 'none', fontFamily: 'var(--font)',
              }}
            >
              {loadingM
                ? <option>Loading meetings...</option>
                : meetings.length === 0
                  ? <option>No meetings found</option>
                  : meetings.map(m => {
                      // Format: "standup.mp4 · Jun 15"
                      const name = (m.filename || 'Untitled Meeting').slice(0, 22)
                      const date = m.created_at
                        ? new Date(m.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                        : ''
                      return (
                        <option key={m.id} value={m.id}>
                          {date ? `${name} · ${date}` : name}
                        </option>
                      )
                    })
              }
            </select>
            <ChevronDown
              size={13} color={T.text3}
              style={{
                position: 'absolute', right: '10px',
                top: '50%', transform: 'translateY(-50%)',
                pointerEvents: 'none',
              }}
            />
          </div>
        </>
      )}

      {/* Current context pill */}
      <div style={{
        padding: '9px 12px',
        borderRadius: '9px',
        background: T.accentBg,
        border: `1px solid ${T.accent}22`,
        fontSize: '12px', color: T.text3,
        lineHeight: 1.5,
      }}>
        {mode === 'single' && selectedMeeting
          ? <>
              <div style={{ fontWeight: 700, color: T.accentLight, marginBottom: '2px' }}>
                Active Meeting
              </div>
              {(selectedMeeting.filename || 'Untitled').slice(0, 28)}
            </>
          : <>
              <div style={{ fontWeight: 700, color: T.accentLight, marginBottom: '2px' }}>
                Search Scope
              </div>
              All {meetings.length} meetings
            </>
        }
      </div>

      {/* Clear */}
      {messages.length > 0 && (
        <button
          onClick={() => { setMessages([]); setSources(null) }}
          style={{
            marginTop: '12px', width: '100%',
            padding: '8px', borderRadius: '9px',
            fontSize: '12.5px', fontWeight: 600,
            color: T.text3, background: 'transparent',
            border: `1px solid ${T.border}`,
            cursor: 'pointer', transition: 'all 0.15s ease',
            fontFamily: 'var(--font)',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = T.danger
            e.currentTarget.style.borderColor = T.danger + '44'
            e.currentTarget.style.background = T.dangerBg
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = T.text3
            e.currentTarget.style.borderColor = T.border
            e.currentTarget.style.background = 'transparent'
          }}
        >
          Clear Chat
        </button>
      )}
    </>
  )
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function Chat() {
  const { T }          = useTheme()
  const { isMobile }   = useScreenSize()
  const [searchParams] = useSearchParams()

  const [meetings,   setMeetings]   = useState([])
  const [mode,       setMode]       = useState('single')
  const [selId,      setSelId]      = useState(
    searchParams.get('meeting') ? Number(searchParams.get('meeting')) : null
  )
  const [messages,   setMessages]   = useState([])
  const [input,      setInput]      = useState('')
  const [loading,    setLoading]    = useState(false)
  const [loadingM,   setLoadingM]   = useState(true)
  const [sources,    setSources]    = useState(null)
  // FIX: on mobile, the Scope/Meeting controls collapse into this toggle
  // instead of a permanent 224px-wide column that never fit the screen.
  const [filtersOpen, setFiltersOpen] = useState(false)

  const bottomRef  = useRef()
  const inputRef   = useRef()

  // FIX: getMeetings returns { items, has_more, next_cursor } — extract items safely.
  // Also show most recent first (API already returns newest first).
  // Limit 100 is fine for a dropdown — users with >100 meetings can search by name.
  useEffect(() => {
    getMeetings({ limit: 100 })
      .then(data => {
        // Handle both paginated { items: [...] } and legacy plain array response
        const m = Array.isArray(data) ? data : (data.items || [])
        setMeetings(m)
        // Pre-select meeting from URL param, or first in list
        const paramId = searchParams.get('meeting')
        if (paramId) {
          setSelId(Number(paramId))
        } else if (m.length > 0) {
          setSelId(m[0].id)
        }
      })
      .catch(() => setMeetings([]))
      .finally(() => setLoadingM(false))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || loading) return
    if (mode === 'single' && !selId) return

    setMessages(m => [...m, { role: 'user', content: q }])
    setInput('')
    setLoading(true)
    setSources(null)

    try {
      const res = mode === 'single'
        ? await chatWithMeeting(q, selId)
        : await chatAcrossMeetings(q)

      setMessages(m => [...m, {
        role:    'assistant',
        content: res.answer,
        sources: res.sources || [],
      }])
    } catch (e) {
      setMessages(m => [...m, {
        role:    'assistant',
        content: `⚠️ ${e.message || 'Something went wrong.'}`,
        sources: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  const selectedMeeting = meetings.find(m => m.id === selId)
  const suggestions = mode === 'single' ? SUGGESTIONS_SINGLE : SUGGESTIONS_CROSS
  const showSuggestions = messages.length === 0

  return (
    // FIX: was `height: calc(100vh - 80px)` — a magic number tuned for
    // desktop that ignored the mobile top bar (52px) and bottom nav (~64px +
    // safe area) Layout.jsx reserves via its own padding. That mismatch is
    // why the input box ended up hidden behind the fixed bottom nav on
    // mobile. `height: '100%'` fills exactly what Layout's content wrapper
    // actually gives this page at any breakpoint — no magic numbers needed,
    // since the flex chain from <body> down already resolves that value.
    <div className="page-enter" style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
        <PageHeader
          title="Meeting Chat"
          subtitle={isMobile ? undefined : 'Ask questions about your meetings using AI.'}
        />

        {/* FIX: on mobile, the Scope/Meeting controls that used to be a
            permanent 224px column now live behind this single button,
            opening a bottom-sheet. Keeps the chat itself full-width. */}
        {isMobile && (
          <button
            onClick={() => setFiltersOpen(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: '6px',
              padding: '8px 12px', borderRadius: '10px', flexShrink: 0,
              marginTop: '2px',
              border: `1px solid ${T.border}`,
              background: T.surface, color: T.text2,
              fontSize: '12.5px', fontWeight: 600, cursor: 'pointer',
              fontFamily: 'inherit', whiteSpace: 'nowrap',
            }}
          >
            <SlidersHorizontal size={13} />
            {mode === 'single' ? 'Meeting' : 'All'}
          </button>
        )}
      </div>

      <div style={{
        display: 'flex', gap: '16px',
        flex: 1, minHeight: 0,
      }}>

        {/* ── Left controls — desktop/tablet only, permanent column ── */}
        {!isMobile && (
          <div style={{ width: '224px', flexShrink: 0 }}>
            <Card style={{ padding: '18px' }}>
              <FiltersPanel
                mode={mode} setMode={setMode} setSources={setSources}
                selId={selId} setSelId={setSelId} setMessages={setMessages}
                loadingM={loadingM} meetings={meetings}
                selectedMeeting={selectedMeeting} messages={messages} T={T}
              />
            </Card>
          </div>
        )}

        {/* ── Chat area ── */}
        <div style={{
          flex: 1, display: 'flex', gap: '14px',
          minHeight: 0, minWidth: 0,
        }}>

          {/* Main chat */}
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column',
            minHeight: 0, minWidth: 0,
          }}>
            <Card style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              padding: 0, overflow: 'hidden', minHeight: 0,
            }}>

              {/* Messages / suggestions */}
              <div style={{
                flex: 1, overflowY: 'auto',
                display: 'flex', flexDirection: 'column',
              }}>
                {showSuggestions ? (
                  <Suggestions
                    suggestions={suggestions}
                    onSelect={q => { setInput(q); inputRef.current?.focus() }}
                    T={T}
                    isMobile={isMobile}
                  />
                ) : (
                  <div style={{
                    padding: isMobile ? '14px' : '20px',
                    display: 'flex', flexDirection: 'column', gap: '16px',
                  }}>
                    {messages.map((msg, i) => (
                      <ChatMessage
                        key={i} msg={msg} T={T}
                        onShowSources={setSources}
                      />
                    ))}
                    {loading && <TypingIndicator T={T} />}
                    <div ref={bottomRef} />
                  </div>
                )}
              </div>

              {/* Input bar */}
              <div style={{
                padding: isMobile ? '10px 12px' : '14px 16px',
                borderTop: `1px solid ${T.border}`,
                display: 'flex', gap: '10px', alignItems: 'flex-end',
                // FIX: keeps the input clear of the phone's home-indicator /
                // gesture bar area when the keyboard isn't up.
                paddingBottom: isMobile ? 'calc(10px + env(safe-area-inset-bottom))' : '14px',
              }}>
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault(); send()
                    }
                  }}
                  placeholder={
                    mode === 'single' && !selId
                      ? 'Select a meeting first...'
                      : isMobile ? 'Ask a question...' : 'Ask a question... (Enter to send, Shift+Enter for new line)'
                  }
                  rows={1}
                  style={{
                    flex: 1, resize: 'none', minWidth: 0,
                    padding: '10px 14px',
                    borderRadius: '10px',
                    border: `1px solid ${T.inputBorder}`,
                    background: T.inputBg,
                    color: T.text, fontSize: '14px',
                    lineHeight: 1.5, outline: 'none',
                    transition: 'border-color 0.15s ease',
                    fontFamily: 'var(--font)',
                  }}
                  onFocus={e => e.target.style.borderColor = T.borderFocus}
                  onBlur={e => e.target.style.borderColor = T.inputBorder}
                  disabled={mode === 'single' && !selId}
                />
                <Button
                  onClick={() => send()}
                  disabled={!input.trim() || loading || (mode === 'single' && !selId)}
                  loading={loading}
                  icon={<Send size={14} />}
                >
                  {isMobile ? '' : 'Send'}
                </Button>
              </div>
            </Card>
          </div>

          {/* Sources panel — inline column on desktop, full-screen overlay on mobile */}
          {sources && (
            <SourcesPanel
              sources={sources}
              onClose={() => setSources(null)}
              T={T}
              isMobile={isMobile}
            />
          )}
        </div>
      </div>

      {/* ── Mobile filter sheet ──────────────────────────────────────────
          Same FiltersPanel content as the desktop column, presented as a
          bottom sheet triggered by the button next to the page title. */}
      {isMobile && filtersOpen && (
        <>
          <div
            onClick={() => setFiltersOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.55)', zIndex: 500 }}
          />
          <div
            className="anim-fade-up"
            style={{
              position: 'fixed', left: 0, right: 0, bottom: 0, zIndex: 501,
              background: T.surface,
              borderTop: `1px solid ${T.border}`,
              borderRadius: '18px 18px 0 0',
              padding: '18px 18px calc(18px + env(safe-area-inset-bottom))',
              maxHeight: '80vh', overflowY: 'auto',
              boxShadow: '0 -12px 40px rgba(0,0,0,0.35)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <span style={{ fontSize: '15px', fontWeight: 750, color: T.text }}>Chat Settings</span>
              <button
                onClick={() => setFiltersOpen(false)}
                style={{
                  width: 28, height: 28, borderRadius: '8px',
                  background: T.surface2, border: `1px solid ${T.border}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', color: T.text3,
                }}
              >
                <X size={14} />
              </button>
            </div>
            <FiltersPanel
              mode={mode} setMode={setMode} setSources={setSources}
              selId={selId} setSelId={setSelId} setMessages={setMessages}
              loadingM={loadingM} meetings={meetings}
              selectedMeeting={selectedMeeting} messages={messages} T={T}
            />
          </div>
        </>
      )}
    </div>
  )
}