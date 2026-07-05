// client/src/pages/Demo.jsx

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft, FileText, Zap, CheckSquare,
  Tag, MessageSquare, ArrowRight
} from 'lucide-react'
import { useTheme } from '../ThemeContext'
import { useAuth } from '../context/AuthContext'
import Navbar from '../components/Navbar'

// ── Preloaded demo meeting data ───────────────────────────────────────────────
const DEMO = {
title: 'Q3 Product Launch Planning',
date: 'June 3, 2024',
duration: '48 minutes',

summary: `The team aligned on the Q3 product launch strategy and confirmed a target release date of July 15th. Marketing committed to delivering campaign assets by July 1st, while Engineering highlighted a potential delay in the payment integration module. A dedicated sprint was approved to mitigate the risk. Arjit proposed onboarding improvements to reduce first-time user friction, which the team agreed to prioritize before launch. Weekly progress syncs were scheduled every Monday at 10am to ensure alignment across teams.`,

topics: [
{
title: 'Q3 Launch Timeline',
description: 'Release date confirmed for July 15th',
},
{
title: 'Marketing Readiness',
description: 'Campaign assets and launch announcements',
},
{
title: 'Payment Integration',
description: 'Risk mitigation and sprint planning',
},
{
title: 'User Onboarding Improvements',
description: 'Reducing friction for new users',
},
{
title: 'Team Coordination',
description: 'Weekly launch sync process',
},
],

decisions: [
{
decision: 'Launch date confirmed as July 15th',
rationale: 'Provides sufficient buffer for QA, marketing, and deployment.',
},
{
decision: 'Dedicated payment integration sprint approved',
rationale: 'Critical feature must be stable before launch.',
},
{
decision: 'New onboarding flow will be included in launch scope',
rationale: 'Expected to improve activation and user retention.',
},
{
decision: 'Weekly Monday sync established',
rationale: 'Ensures cross-functional alignment through launch.',
},
],

action_items: [
{
task: 'Finalize marketing campaign assets',
owner: 'Pankaj',
deadline: 'July 1st',
priority: 'high',
},
{
task: 'Complete payment integration module',
owner: 'Shashwat',
deadline: 'July 8th',
priority: 'high',
},
{
task: 'Design updated onboarding experience',
owner: 'Arjit',
deadline: 'June 25th',
priority: 'high',
},
{
task: 'Prepare QA test plan',
owner: 'Vaibhav',
deadline: 'July 10th',
priority: 'high',
},
{
task: 'Send recurring Monday sync invites',
owner: 'Shashwat',
deadline: 'This week',
priority: 'medium',
},
{
task: 'Draft launch announcement email',
owner: 'Pankaj',
deadline: 'July 12th',
priority: 'medium',
},
],

transcript: `Pankaj: Good morning everyone. Let's begin our Q3 product launch planning session. Our primary goal today is confirming launch readiness and identifying any risks.

Shashwat: Engineering is largely on track for the July 15th target. The only concern is the payment integration module. We could face a two-day delay depending on API testing results.

Pankaj: How serious is that risk?

Shashwat: The module is critical because it powers checkout and subscriptions. Without it, we can't launch.

Vaibhav: Can we dedicate a focused sprint next week to close the gap?

Shashwat: Yes. A one-week sprint should recover the lost time.

Pankaj: Approved. Let's prioritize that immediately.

Arjit: While we're discussing launch readiness, I'd like to raise one product concern. User testing showed that new users struggle during onboarding. We saw a noticeable drop-off after account creation.

Pankaj: What's your recommendation?

Arjit: We simplify onboarding into three steps and add contextual guidance. The changes aren't technically heavy and could improve activation significantly.

Shashwat: Engineering can support those changes without impacting the launch timeline.

Vaibhav: From a QA perspective, that's manageable as well.

Pankaj: Great. Let's include onboarding improvements in the launch scope.

Pankaj: Marketing update?

Poorvansh: Campaign assets are progressing well. Landing pages, social creatives, and launch emails will be ready by July 1st.

Pankaj: Excellent. That gives us two weeks for reviews.

Arjit: We should also update product screenshots after the onboarding redesign is complete.

Poorvansh: Good point. We'll schedule that into the marketing timeline.

Pankaj: I'd also like to establish a recurring launch sync meeting. Mondays at 10am?

Shashwat: Works for engineering.

Vaibhav: Works for QA.

Arjit: Works for product.

Poorvansh: Marketing is available as well.

Pankaj: Perfect. Let's lock it in.

Shashwat: I'll send calendar invites today.

Pankaj: To summarize: launch remains July 15th, engineering will run a dedicated sprint for payment integration, onboarding improvements are approved, marketing assets are due July 1st, and we'll meet every Monday at 10am until launch.

All: Sounds good.

Pankaj: Great work everyone. Let's make this launch a success.`
}

// ── Section header ─────────────────────────────────────────────────────────────
function SectionHead({ icon, title, count, color, bg }) {
  const { T, isDark } = useTheme()
  return (
    <div className="page-enter" style={{
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between', marginBottom: '18px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '8px',
          background: bg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {icon}
        </div>
        <span style={{
          fontSize: '16px', fontWeight: 700,
          color: T.text, letterSpacing: '-0.02em',
        }}>
          {title}
        </span>
      </div>
      {count !== undefined && (
        <span style={{
          padding: '2px 10px', borderRadius: '99px',
          fontSize: '12px', fontWeight: 700,
          color, background: bg,
        }}>
          {count}
        </span>
      )}
    </div>
  )
}

export default function Demo() {
  const { T, isDark }   = useTheme() 
  const { isAuthenticated } = useAuth()
  const navigate        = useNavigate()
  const [activeTab, setActiveTab] = useState('summary')

  const tabs = [
    { id: 'summary',   label: 'Summary'      },
    { id: 'decisions', label: 'Decisions'    },
    { id: 'actions',   label: 'Action Items' },
    { id: 'transcript',label: 'Transcript'   },
  ]

  const priorityColor = (p) => {
    if (p === 'high') return { color: T.danger,  bg: T.dangerBg  }
    if (p === 'low')  return { color: T.emerald, bg: T.emeraldBg }
    return                    { color: T.warning, bg: T.warningBg }
  }

  return (
    <div style={{ background: T.bg, minHeight: '100vh' }}>
      <Navbar />

      <div style={{
        maxWidth: '960px', margin: '0 auto',
        padding: '100px 32px 60px',
      }}>

        {/* Back */}
        <button
          onClick={() => navigate('/')}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '6px',
            fontSize: '13px', fontWeight: 600, color: T.text3,
            background: 'none', border: 'none', cursor: 'pointer',
            marginBottom: '28px', padding: 0,
            marginRight: '14px',
            transition: 'color 0.15s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.color = T.text}
          onMouseLeave={e => e.currentTarget.style.color = T.text3}
        >
          <ArrowLeft size={14} /> Back to Home
        </button>

        {/* Demo badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: '5px 14px', borderRadius: '99px',
          background: T.accentBg, border: `1px solid ${T.accent}33`,
          fontSize: '12px', fontWeight: 700,
          color: T.accentLight, marginBottom: '16px',
        }}>
          ✨ Live Demo Meeting
        </div>

        {/* Header */}
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{
            fontSize: '32px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            margin: '0 0 12px',
          }}>
            {DEMO.title}
          </h1>
          <div style={{
            display: 'flex', gap: '20px', flexWrap: 'wrap',
          }}>
            {[
              { icon: '📅', text: DEMO.date     },
              { icon: '⏱️', text: DEMO.duration  },
              { icon: '🤖', text: 'AI Processed' },
            ].map(item => (
              <span key={item.text} style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                fontSize: '13px', color: T.text3, fontWeight: 500,
              }}>
                {item.icon} {item.text}
              </span>
            ))}
          </div>
        </div>

        {/* Quick stats */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '12px', marginBottom: '28px',
        }}>
          {[
            { label: 'Topics',       value: DEMO.topics.length,       icon: '🏷️', color: T.cyanText,   bg: T.cyanBg   },
            { label: 'Decisions',    value: DEMO.decisions.length,    icon: '⚡',  color: T.purpleText, bg: T.purpleBg },
            { label: 'Action Items', value: DEMO.action_items.length, icon: '✅',  color: T.orangeText, bg: T.orangeBg },
            { label: 'Participants', value: 4,                        icon: '👥',  color: T.blueText,   bg: T.blueBg   },
          ].map(s => (
            <div key={s.label} style={{
              padding: '16px', borderRadius: '14px',
              background: T.surface, border: `1px solid ${T.border}`,
              boxShadow: T.cardShadow,
              display: 'flex', alignItems: 'center', gap: '12px',
            }}>
              <div style={{
                width: '34px', height: '34px', borderRadius: '8px',
                background: s.bg, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '16px',
              }}>
                {s.icon}
              </div>
              <div>
                <div style={{
                  fontSize: '22px', fontWeight: 800,
                  letterSpacing: '-0.04em', color: T.text, lineHeight: 1,
                }}>
                  {s.value}
                </div>
                <div style={{
                  fontSize: '11px', fontWeight: 600,
                  color: T.text3, marginTop: '2px',
                  textTransform: 'uppercase', letterSpacing: '0.04em',
                }}>
                  {s.label}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Tab switcher */}
        <div style={{
          display: 'flex', gap: '4px',
          background: T.surface2, border: `1px solid ${T.border}`,
          borderRadius: '12px', padding: '4px',
          marginBottom: '24px', width: 'fit-content',
        }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 18px', borderRadius: '9px',
                fontSize: '13.5px', fontWeight: activeTab === tab.id ? 650 : 450,
                color: activeTab === tab.id ? T.text : T.text3,
                background: activeTab === tab.id ? T.surface : 'transparent',
                border: `1px solid ${activeTab === tab.id ? T.border : 'transparent'}`,
                cursor: 'pointer', transition: 'all 0.15s ease',
                boxShadow: activeTab === tab.id ? T.cardShadow : 'none',
                fontFamily: 'var(--font)',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="anim-fade-in" style={{
          background: T.surface, border: `1px solid ${T.border}`,
          borderRadius: '18px', padding: '28px',
          boxShadow: T.cardShadow,
        }}>

          {activeTab === 'summary' && (
            <div>
              <SectionHead
                icon={<FileText size={16} color={T.blueText} />}
                title="Executive Summary"
                color={T.blueText} bg={T.blueBg}
              />
              <p style={{
                fontSize: '16px', fontWeight: 400,
                color: T.text2, lineHeight: 1.8, margin: '0 0 24px',
              }}>
                {DEMO.summary}
              </p>

              <SectionHead
                icon={<Tag size={16} color={T.cyanText} />}
                title="Topics Discussed"
                count={DEMO.topics.length}
                color={T.cyanText} bg={T.cyanBg}
              />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {DEMO.topics.map((t, i) => (
                  <div key={i} style={{
                    padding: '8px 16px', borderRadius: '99px',
                    background: T.cyanBg, border: `1px solid ${T.cyan}22`,
                  }}>
                    <div style={{
                      fontSize: '13px', fontWeight: 650,
                      color: T.cyanText,
                    }}>
                      {t.title}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'decisions' && (
            <div>
              <SectionHead
                icon={<Zap size={16} color={T.purpleText} />}
                title="Decisions Made"
                count={DEMO.decisions.length}
                color={T.purpleText} bg={T.purpleBg}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {DEMO.decisions.map((d, i) => (
                  <div key={i} style={{
                    padding: '14px 16px', borderRadius: '10px',
                    background: T.purpleBg, border: `1px solid ${T.purple}22`,
                  }}>
                    <div style={{
                      fontSize: '14px', fontWeight: 600,
                      color: T.text, lineHeight: 1.5, marginBottom: '5px',
                    }}>
                      {d.decision}
                    </div>
                    <div style={{
                      fontSize: '13px', color: T.text3,
                      fontStyle: 'italic',
                    }}>
                      ↳ {d.rationale}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'actions' && (
            <div>
              <SectionHead
                icon={<CheckSquare size={16} color={T.orangeText} />}
                title="Action Items"
                count={DEMO.action_items.length}
                color={T.orangeText} bg={T.orangeBg}
              />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '9px' }}>
                {DEMO.action_items.map((item, i) => {
                  const pc = priorityColor(item.priority)
                  return (
                    <div key={i} style={{
                      display: 'flex', alignItems: 'flex-start',
                      justifyContent: 'space-between', gap: '14px',
                      padding: '13px 16px', borderRadius: '10px',
                      background: T.surface2, border: `1px solid ${T.border}`,
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{
                          fontSize: '14px', fontWeight: 600,
                          color: T.text, marginBottom: '5px',
                        }}>
                          {item.task}
                        </div>
                        <div style={{
                          display: 'flex', gap: '12px',
                          fontSize: '12px', color: T.text3,
                        }}>
                          {item.owner    && <span>👤 {item.owner}</span>}
                          {item.deadline && <span>📅 {item.deadline}</span>}
                        </div>
                      </div>
                      <span style={{
                        padding: '3px 10px', borderRadius: '99px',
                        fontSize: '11px', fontWeight: 700,
                        color: pc.color, background: pc.bg,
                        flexShrink: 0,
                      }}>
                        {item.priority}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {activeTab === 'transcript' && (
            <div>
              <SectionHead
                icon={<FileText size={16} color={T.text3} />}
                title="Transcript"
                color={T.text3} bg={T.surface3}
              />
              <div style={{
                maxHeight: '400px', overflowY: 'auto',
                padding: '20px', borderRadius: '10px',
                background: T.surface2, border: `1px solid ${T.border}`,
                fontSize: '14px', color: T.text2,
                lineHeight: 1.85, whiteSpace: 'pre-line',
              }}>
                {DEMO.transcript}
              </div>
            </div>
          )}
        </div>

        {/* CTA */}
        <div style={{
          marginTop: '40px', padding: '36px',
          background: T.surface,
          border: `1px solid ${T.border}`,
          borderRadius: '20px',
          boxShadow: T.cardShadow,
          textAlign: 'center',
        }}>
          <div style={{
            fontSize: '22px', fontWeight: 800,
            letterSpacing: '-0.04em', color: T.text,
            marginBottom: '10px',
          }}>
            Ready to analyze your own meetings?
          </div>
          <div style={{
            fontSize: '15px', color: T.text3,
            marginBottom: '24px', lineHeight: 1.6,
          }}>
            Create a free account and upload your first recording in minutes.
          </div>
          <div style={{
            display: 'flex', gap: '12px',
            justifyContent: 'center', flexWrap: 'wrap',
          }}>
            {isAuthenticated ? (
              <button
                onClick={() => navigate('/app/upload')}
                style={{
                  padding: '13px 32px', borderRadius: '12px',
                  background: isDark ? '#10b981' : '#059669', border: 'none',
                  color: '#fff', fontSize: '15px', fontWeight: 700,
                  cursor: 'pointer', boxShadow: T.btnShadow,
                  display: 'inline-flex', alignItems: 'center', gap: '8px',
                  fontFamily: 'var(--font)',
                }}
              >
                Upload Meeting <ArrowRight size={16} />
              </button>
            ) : (
              <>
                <button
                  onClick={() => navigate('/register')}
                  style={{
                    padding: '13px 32px', borderRadius: '12px',
                    background: isDark ? '#10b981' : '#059669', border: 'none',
                    color: '#fff', fontSize: '15px', fontWeight: 700,
                    cursor: 'pointer', boxShadow: T.btnShadow,
                    display: 'inline-flex', alignItems: 'center', gap: '8px',
                    fontFamily: 'var(--font)',
                  }}
                >
                  Create Free Account <ArrowRight size={16} />
                </button>
                <button
                  onClick={() => navigate('/login')}
                  style={{
                    padding: '13px 24px', borderRadius: '12px',
                    background: T.surface2, border: `1px solid ${T.border}`,
                    color: T.text2, fontSize: '15px', fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'var(--font)',
                  }}
                >
                  Sign In
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}