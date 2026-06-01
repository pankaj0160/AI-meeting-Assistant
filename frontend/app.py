"""
Summly Streamlit Frontend
Phase 2 Complete with Theme Toggle, History, and Intelligence Display
"""

import streamlit as st
import requests
from datetime import datetime
import json

# =====================================================
# CONFIG
# =====================================================

BACKEND_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Summly — Meeting Intelligence",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True

if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = ""

if "intelligence_data" not in st.session_state:
    st.session_state.intelligence_data = None

if "selected_meeting_id" not in st.session_state:
    st.session_state.selected_meeting_id = None

if "meetings_list" not in st.session_state:
    st.session_state.meetings_list = []

# =====================================================
# THEME DEFINITIONS
# =====================================================

DARK = {
    "bg":           "#080d1a",
    "surface":      "#0f1729",
    "surface2":     "#141e33",
    "surface3":     "#1a2540",
    "border":       "#1e2d4a",
    "border2":      "#263555",
    "accent":       "#3b82f6",
    "accent2":      "#8b5cf6",
    "accent3":      "#06b6d4",
    "accent_glow":  "rgba(59,130,246,0.15)",
    "text":         "#f0f4ff",
    "text2":        "#94a3b8",
    "text3":        "#64748b",
    "success":      "#10b981",
    "warning":      "#f59e0b",
    "danger":       "#ef4444",
    "card_shadow":  "0 4px 24px rgba(0,0,0,0.4)",
    "hero_grad":    "linear-gradient(135deg, #0f1729 0%, #1a1040 50%, #0a1628 100%)",
    "btn_grad":     "linear-gradient(135deg, #3b82f6, #8b5cf6)",
    "tag_bg":       "rgba(59,130,246,0.12)",
    "tag_text":     "#93c5fd",
}

LIGHT = {
    "bg":           "#f8faff",
    "surface":      "#ffffff",
    "surface2":     "#f1f5fd",
    "surface3":     "#e8eef8",
    "border":       "#dde5f4",
    "border2":      "#c8d5ec",
    "accent":       "#2563eb",
    "accent2":      "#7c3aed",
    "accent3":      "#0891b2",
    "accent_glow":  "rgba(37,99,235,0.08)",
    "text":         "#0f172a",
    "text2":        "#475569",
    "text3":        "#94a3b8",
    "success":      "#059669",
    "warning":      "#d97706",
    "danger":       "#dc2626",
    "card_shadow":  "0 2px 16px rgba(0,0,0,0.08)",
    "hero_grad":    "linear-gradient(135deg, #eff6ff 0%, #f5f0ff 50%, #ecfeff 100%)",
    "btn_grad":     "linear-gradient(135deg, #2563eb, #7c3aed)",
    "tag_bg":       "rgba(37,99,235,0.08)",
    "tag_text":     "#1d4ed8",
}

T = DARK if st.session_state.dark_mode else LIGHT

# =====================================================
# GLOBAL CSS
# =====================================================

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600&display=swap');

* {{ box-sizing: border-box; }}

.stApp {{
    background-color: {T["bg"]};
    font-family: 'DM Sans', sans-serif;
    color: {T["text"]};
}}

#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1300px; }}

section[data-testid="stSidebar"] {{
    background: {T["surface"]} !important;
    border-right: 1px solid {T["border"]} !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    background: {T["surface2"]};
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
    border: 1px solid {T["border"]};
}}

.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    color: {T["text2"]};
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    padding: 8px 20px;
    background: transparent;
}}

.stTabs [aria-selected="true"] {{
    background: {T["accent"]} !important;
    color: white !important;
}}

.stButton > button {{
    background: {T["btn_grad"]} !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.5rem !important;
    width: 100% !important;
    letter-spacing: 0.02em !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 14px rgba(59,130,246,0.3) !important;
}}

.stButton > button:hover {{
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(59,130,246,0.4) !important;
}}

.stTextInput > div > div > input {{
    background: {T["surface2"]} !important;
    border: 1px solid {T["border"]} !important;
    border-radius: 10px !important;
    color: {T["text"]} !important;
    padding: 12px 16px !important;
}}

.stFileUploader {{
    background: {T["surface2"]} !important;
    border: 2px dashed {T["border2"]} !important;
    border-radius: 14px !important;
}}

.stDownloadButton > button {{
    background: {T["surface2"]} !important;
    color: {T["accent"]} !important;
    border: 1px solid {T["border"]} !important;
    border-radius: 10px !important;
    width: 100% !important;
}}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def backend_online():
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return r.status_code == 200
    except:
        return False

def fetch_meetings():
    try:
        r = requests.get(f"{BACKEND_URL}/meetings", timeout=5)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return []

def fetch_meeting_detail(meeting_id: int):
    try:
        r = requests.get(f"{BACKEND_URL}/meetings/{meeting_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def fmt_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", ""))
        return dt.strftime("%b %d · %H:%M")
    except:
        return iso_str[:16] if iso_str else "—"

def priority_color(p):
    p = (p or "medium").lower()
    if p == "high":   return T["danger"]
    if p == "low":    return T["success"]
    return T["warning"]

def status_badge(s):
    s = (s or "open").lower()
    color = T["warning"] if s == "open" else T["success"]
    return f'<span style="background:{color}22;color:{color};padding:3px 10px;border-radius:16px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">{s}</span>'

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    
    # Logo + theme toggle
    col_logo, col_toggle = st.columns([3, 1])
    with col_logo:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
            <div style="width:32px;height:32px;background:{T['btn_grad']};border-radius:8px;
                        display:flex;align-items:center;justify-content:center;font-size:18px;">🎙</div>
            <span style="font-family:'Syne',sans-serif;font-weight:800;font-size:20px;
                         color:{T['text']};letter-spacing:-0.5px;">Summly</span>
        </div>
        <p style="font-size:11px;color:{T['text3']};margin:0;font-style:italic;">
            AI Meeting Intelligence
        </p>
        """, unsafe_allow_html=True)
    
    with col_toggle:
        st.markdown("<div style='margin-top:4px;'>", unsafe_allow_html=True)
        theme_icon = "☀️" if st.session_state.dark_mode else "🌙"
        if st.button(theme_icon, key="theme_btn", help="Toggle theme"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown(f"<hr style='border-color:{T['border']};margin:16px 0;'>", unsafe_allow_html=True)
    
    # Backend status
    online = backend_online()
    status_color = T["success"] if online else T["danger"]
    status_text = "Backend Online" if online else "Backend Offline"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;
                background:{status_color}18;border:1px solid {status_color}44;
                border-radius:8px;margin-bottom:16px;">
        <span style="color:{status_color};font-size:10px;">●</span>
        <span style="font-size:13px;color:{status_color};font-weight:500;">{status_text}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Past meetings
    st.markdown(f"""
    <p style="font-family:'Syne',sans-serif;font-size:12px;font-weight:700;
               color:{T['text3']};letter-spacing:0.1em;text-transform:uppercase;
               margin:0 0 10px 0;">Recent Meetings</p>
    """, unsafe_allow_html=True)
    
    meetings = fetch_meetings()
    if meetings:
        for m in meetings[:8]:
            mid = m.get("id", "")
            fname = m.get("filename", "Untitled")[:28]
            cdate = fmt_date(m.get("created_at", ""))
            is_sel = (st.session_state.selected_meeting_id == mid)
            bg = T["accent_glow"] if is_sel else "transparent"
            border = T["accent"] if is_sel else "transparent"
            
            if st.button(
                f"🎙 {fname}\n{cdate}",
                key=f"view_{mid}",
                use_container_width=True,
                help=f"View {fname}"
            ):
                st.session_state.selected_meeting_id = mid
                meeting = fetch_meeting_detail(mid)
                if meeting:
                    st.session_state.transcript_text = meeting.get("transcript", "")
                    st.session_state.intelligence_data = meeting.get("intelligence")
                st.rerun()
    else:
        st.info("No meetings yet. Process one to get started.")
    
    st.markdown(f"<hr style='border-color:{T['border']};margin:16px 0;'>", unsafe_allow_html=True)
    
    # Features
    features = [
        ("✅", "File Upload"),
        ("✅", "YouTube Transcription"),
        ("✅", "AI Meeting Summary"),
        ("✅", "Action Item Extraction"),
        ("✅", "Decision Tracking"),
        ("✅", "Topic Analysis"),
        ("🚀", "Meeting Chat (Phase 3)"),
        ("🚀", "Cross-Meeting Search"),
    ]
    
    st.markdown(f"""
    <p style="font-family:'Syne',sans-serif;font-size:12px;font-weight:700;
               color:{T['text3']};letter-spacing:0.1em;text-transform:uppercase;
               margin:0 0 10px 0;">Features</p>
    """, unsafe_allow_html=True)
    
    for icon, label in features:
        color = T["text2"] if icon == "✅" else T["text3"]
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;padding:4px 0;
                    font-size:13px;color:{color};">
            <span>{icon}</span><span>{label}</span>
        </div>
        """, unsafe_allow_html=True)

# =====================================================
# HERO SECTION
# =====================================================

hero_color = T["text"] if not st.session_state.dark_mode else "#f0f4ff"
accent_line = f"linear-gradient(90deg, {T['accent']}, {T['accent2']}, {T['accent3']})"

st.markdown(f"""
<div style="background:{T['hero_grad']};padding:2.5rem 3rem;border-radius:20px;
            border:1px solid {T['border']};margin-bottom:2rem;
            box-shadow:{T['card_shadow']};position:relative;overflow:hidden;">
    <div style="position:absolute;top:0;left:0;right:0;height:3px;background:{accent_line};"></div>
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;">
        <div>
            <h1 style="font-family:'Syne',sans-serif;font-size:2.4rem;font-weight:800;
                        margin:0;letter-spacing:-1px;color:{hero_color};">
                Meeting Intelligence Platform
            </h1>
            <p style="color:{T['text2']};font-size:1rem;margin:8px 0 0 0;font-weight:300;">
                Upload recordings · Get structured intelligence · Track decisions & actions
            </p>
        </div>
        <div style="display:flex;gap:16px;align-items:center;">
            <div style="text-align:center;">
                <div style="font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:800;
                             background:{accent_line};-webkit-background-clip:text;
                             -webkit-text-fill-color:transparent;">{len(meetings)}</div>
                <div style="font-size:12px;color:{T['text3']};margin-top:2px;text-transform:uppercase;">Meetings</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# =====================================================
# MAIN CONTENT TABS
# =====================================================

tab1, tab2 = st.tabs(["  📁  Upload File  ", "  🎥  YouTube URL  "])

# ── Upload Tab ──────────────────────────────────────

with tab1:
    uploaded_file = st.file_uploader(
        "Drop your audio or video file",
        type=["mp3", "mp4", "wav", "m4a", "webm", "mkv"],
        label_visibility="collapsed"
    )
    
    if uploaded_file:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:14px 18px;
                    background:{T['accent_glow']};border:1px solid {T['border2']};
                    border-radius:10px;margin:12px 0;">
            <span style="font-size:20px;">📎</span>
            <div>
                <div style="font-weight:500;color:{T['text']};font-size:14px;">{uploaded_file.name}</div>
                <div style="font-size:12px;color:{T['text3']};">{round(uploaded_file.size/1024,1)} KB</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Transcribe & Analyze", key="upload_btn", use_container_width=True):
            with st.spinner("Processing your file..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/upload",
                        files={"file": (uploaded_file.name, uploaded_file, uploaded_file.type)},
                        timeout=300
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.transcript_text = data.get("transcript", "")
                        st.session_state.intelligence_data = data.get("intelligence")
                        st.session_state.selected_meeting_id = data.get("meeting_id")
                        st.success("✅ Processing complete!")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

# ── YouTube Tab ─────────────────────────────────────

with tab2:
    youtube_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed"
    )
    
    if st.button("🎥 Download & Analyze", key="yt_btn", use_container_width=True):
        if youtube_url:
            with st.spinner("Downloading and processing..."):
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/youtube",
                        json={"url": youtube_url},
                        timeout=600
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.transcript_text = data.get("transcript", "")
                        st.session_state.intelligence_data = data.get("intelligence")
                        st.session_state.selected_meeting_id = data.get("meeting_id")
                        st.success("✅ Done!")
                        st.rerun()
                    else:
                        st.error(f"Error: {response.json().get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        else:
            st.warning("Please enter a YouTube URL")

# =====================================================
# RESULTS SECTION
# =====================================================

transcript = st.session_state.transcript_text
intel = st.session_state.intelligence_data

if transcript:
    
    # Metrics
    words = len(transcript.split())
    chars = len(transcript)
    mins = max(1, round(words / 150))
    sents = transcript.count(".") + transcript.count("?") + transcript.count("!")
    
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        (m1, words, "Words", "✍️"),
        (m2, mins, "Minutes", "⏱️"),
        (m3, chars, "Characters", "📝"),
        (m4, sents, "Sentences", "💬"),
    ]
    
    for col, val, label, icon in metrics:
        with col:
            st.markdown(f"""
            <div style="background:{T['surface']};padding:18px 20px;border-radius:14px;
                        border:1px solid {T['border']};box-shadow:{T['card_shadow']};
                        text-align:center;">
                <div style="font-size:22px;margin-bottom:4px;">{icon}</div>
                <div style="font-family:'Syne',sans-serif;font-size:1.6rem;font-weight:800;
                             color:{T['accent']};line-height:1;">{val:,}</div>
                <div style="font-size:12px;color:{T['text3']};margin-top:4px;
                             text-transform:uppercase;letter-spacing:0.06em;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    
    # Intelligence report + Transcript
    if intel:
        left, right = st.columns([3, 2], gap="large")
        
        with left:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
                <div style="width:4px;height:24px;background:{T['btn_grad']};border-radius:2px;"></div>
                <h2 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;
                            margin:0;color:{T['text']};letter-spacing:-0.5px;">Intelligence Report</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Summary
            st.markdown(f"""
            <div style="background:{T['surface']};padding:22px 24px;border-radius:16px;
                        border:1px solid {T['border']};margin-bottom:16px;
                        box-shadow:{T['card_shadow']};">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                    <span style="font-size:18px;">📋</span>
                    <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
                                 color:{T['text']};letter-spacing:0.02em;">Executive Summary</span>
                </div>
                <p style="color:{T['text2']};line-height:1.75;font-size:14px;margin:0;
                           font-weight:300;">{intel.get('summary','No summary.')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Topics
            topics = intel.get("topics", [])
            if topics:
                tags = "".join([f"""
                <span style="display:inline-block;background:{T['tag_bg']};color:{T['tag_text']};
                              padding:5px 14px;border-radius:20px;font-size:12px;font-weight:500;
                              margin:4px 4px 0 0;border:1px solid {T['border']};">
                    {t.get('title','')}
                </span>""" for t in topics])
                
                st.markdown(f"""
                <div style="background:{T['surface']};padding:22px 24px;border-radius:16px;
                            border:1px solid {T['border']};margin-bottom:16px;
                            box-shadow:{T['card_shadow']};">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;">
                        <span style="font-size:18px;">🏷️</span>
                        <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
                                     color:{T['text']};">Topics Discussed</span>
                    </div>
                    <div>{tags}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Decisions
            decisions = intel.get("decisions", [])
            if decisions:
                decs = ""
                for d in decisions:
                    rat = f'<div style="font-size:12px;color:{T["text3"]};margin-top:4px;font-style:italic;">↳ {d.get("rationale")}</div>' if d.get("rationale") else ""
                    decs += f"""
                    <div style="padding:12px 0;border-bottom:1px solid {T['border']};">
                        <div style="display:flex;align-items:flex-start;gap:10px;">
                            <span style="color:{T['accent2']};font-size:16px;">⚡</span>
                            <div>
                                <div style="font-size:13px;font-weight:500;color:{T['text']};line-height:1.5;">{d.get('decision','')}</div>
                                {rat}
                            </div>
                        </div>
                    </div>"""
                
                st.markdown(f"""
                <div style="background:{T['surface']};padding:22px 24px;border-radius:16px;
                            border:1px solid {T['border']};margin-bottom:16px;
                            box-shadow:{T['card_shadow']};">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                        <span style="font-size:18px;">⚡</span>
                        <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
                                     color:{T['text']};">Decisions Made</span>
                        <span style="background:{T['accent2']}22;color:{T['accent2']};
                                     padding:2px 10px;border-radius:20px;font-size:11px;
                                     font-weight:700;margin-left:auto;">{len(decisions)}</span>
                    </div>
                    {decs}
                </div>
                """, unsafe_allow_html=True)
            
            # Action Items
            items = intel.get("action_items", [])
            if items:
                rows = ""
                for item in items:
                    p_col = priority_color(item.get("priority"))
                    p_lbl = (item.get("priority") or "medium").title()
                    owner_html = f'<span style="font-size:12px;color:{T["text3"]};">👤 {item["owner"]}</span>' if item.get("owner") else ""
                    deadline_html = f'<span style="font-size:12px;color:{T["text3"]};">📅 {item["deadline"]}</span>' if item.get("deadline") else ""
                    
                    rows += f"""
                    <div style="padding:13px 16px;border-radius:10px;margin-bottom:8px;
                                background:{T['surface2']};border:1px solid {T['border']};">
                        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;">
                            <div style="flex:1;">
                                <div style="font-size:13px;font-weight:500;color:{T['text']};
                                             margin-bottom:6px;">{item.get('task','')}</div>
                                <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;">
                                    {owner_html}
                                    {deadline_html}
                                </div>
                            </div>
                            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;">
                                <span style="background:{p_col}22;color:{p_col};padding:2px 10px;
                                              border-radius:20px;font-size:11px;font-weight:600;
                                              text-transform:uppercase;letter-spacing:0.05em;">{p_lbl}</span>
                                {status_badge(item.get('status','open'))}
                            </div>
                        </div>
                    </div>"""
                
                st.markdown(f"""
                <div style="background:{T['surface']};padding:22px 24px;border-radius:16px;
                            border:1px solid {T['border']};box-shadow:{T['card_shadow']};">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
                        <span style="font-size:18px;">✅</span>
                        <span style="font-family:'Syne',sans-serif;font-weight:700;font-size:14px;
                                     color:{T['text']};">Action Items</span>
                        <span style="background:{T['success']}22;color:{T['success']};
                                     padding:2px 10px;border-radius:20px;font-size:11px;
                                     font-weight:700;margin-left:auto;">{len(items)}</span>
                    </div>
                    {rows}
                </div>
                """, unsafe_allow_html=True)
        
        # Right: Transcript
        with right:
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
                <div style="width:4px;height:24px;background:{T['btn_grad']};border-radius:2px;"></div>
                <h2 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;
                            margin:0;color:{T['text']};">Transcript</h2>
            </div>
            <div style="background:{T['surface']};padding:22px;border-radius:16px;
                        border:1px solid {T['border']};box-shadow:{T['card_shadow']};
                        max-height:700px;overflow-y:auto;line-height:1.85;
                        font-size:13.5px;color:{T['text2']};font-weight:300;">
                {transcript}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            
            dl1, dl2 = st.columns(2)
            with dl1:
                st.download_button(
                    "📥 Transcript",
                    transcript,
                    "transcript.txt",
                    "text/plain"
                )
            with dl2:
                st.download_button(
                    "📄 Full Report",
                    json.dumps({"transcript": transcript, "intelligence": intel}, indent=2),
                    "meeting_report.json",
                    "application/json"
                )
    
    else:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
            <div style="width:4px;height:24px;background:{T['btn_grad']};border-radius:2px;"></div>
            <h2 style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.3rem;
                        margin:0;color:{T['text']};">Transcript</h2>
        </div>
        <div style="background:{T['surface']};padding:28px;border-radius:16px;
                    border:1px solid {T['border']};box-shadow:{T['card_shadow']};
                    line-height:1.9;font-size:15px;color:{T['text2']};">
            {transcript}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        
        dc1, dc2, _ = st.columns([1, 1, 2])
        with dc1:
            st.download_button("📥 Transcript", transcript, "transcript.txt", "text/plain")
        with dc2:
            st.download_button("📄 Report", transcript, "report.md", "text/markdown")

else:
    st.markdown(f"""
    <div style="text-align:center;padding:4rem 2rem;color:{T['text3']};">
        <div style="font-size:56px;margin-bottom:16px;opacity:0.6;">🎙️</div>
        <h3 style="font-family:'Syne',sans-serif;font-weight:700;color:{T['text2']};margin:0 0 8px;">
            No meeting processed yet
        </h3>
        <p style="font-size:14px;max-width:360px;margin:0 auto;line-height:1.7;">
            Upload an audio or video file, or paste a YouTube URL above.
            You'll get a full intelligence report instantly.
        </p>
    </div>
    """, unsafe_allow_html=True)