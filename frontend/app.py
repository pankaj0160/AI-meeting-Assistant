import streamlit as st
import requests

# =====================================================
# CONFIG
# =====================================================

BACKEND_URL = "http://localhost:8080"

st.set_page_config(
    page_title="Summly",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

/* Main App */
.stApp {
    background-color: #0f172a;
    color: white;
}

/* Hide Streamlit Branding */
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

/* Hero Section */
.hero {
    background: linear-gradient(
        135deg,
        #2563eb,
        #7c3aed,
        #06b6d4
    );
    padding: 3rem;
    border-radius: 20px;
    text-align: center;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.hero h1 {
    font-size: 3rem;
    margin-bottom: 0.5rem;
}

.hero p {
    font-size: 1.1rem;
}

/* Metric Cards */
.metric-card {
    background: #1e293b;
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    border: 1px solid #334155;
}

.metric-number {
    font-size: 28px;
    font-weight: bold;
    color: #38bdf8;
}

.metric-label {
    color: #cbd5e1;
}

/* Transcript Box */
.transcript-box {
    background: #111827;
    border-radius: 15px;
    padding: 20px;
    border: 1px solid #334155;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #111827;
}

/* Buttons */
.stButton > button {
    width: 100%;
    background: linear-gradient(
        90deg,
        #2563eb,
        #7c3aed
    );
    color: white;
    border: none;
    border-radius: 10px;
    padding: 0.7rem;
    font-weight: bold;
}

.stButton > button:hover {
    background: linear-gradient(
        90deg,
        #1d4ed8,
        #6d28d9
    );
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("🎙️ Summly")

st.sidebar.markdown("---")

try:
    requests.get(f"{BACKEND_URL}/docs", timeout=3)
    st.sidebar.success("🟢 Backend Online")
except:
    st.sidebar.error("🔴 Backend Offline")

st.sidebar.markdown("---")

st.sidebar.markdown("""
### Features

✅ File Upload

✅ YouTube Transcription

✅ Download Transcript

🚀 AI Summaries (Coming Soon)

🚀 Action Items (Coming Soon)

🚀 Chat with Meetings (Coming Soon)
""")

# =====================================================
# HERO SECTION
# =====================================================

st.markdown("""
<div class="hero">
<h1>🎙️ SUMMLY</h1>
<p>AI Meeting Intelligence Platform</p>
<p>Transform recordings into transcripts, summaries and actionable insights.</p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# TABS
# =====================================================

tab1, tab2 = st.tabs([
    "📁 Upload File",
    "🎥 YouTube URL"
])

transcript_text = ""

# =====================================================
# FILE UPLOAD TAB
# =====================================================

with tab1:

    st.subheader("Upload Audio / Video")

    uploaded_file = st.file_uploader(
        "Supported formats: MP3, MP4, WAV, M4A",
        type=["mp3", "mp4", "wav", "m4a"]
    )

    if uploaded_file:

        st.info(
            f"Selected File: {uploaded_file.name}"
        )

        if st.button("🚀 Transcribe File"):

            try:

                with st.spinner(
                    "🧠 AI is analyzing your meeting..."
                ):

                    response = requests.post(
                        f"{BACKEND_URL}/upload",
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file,
                                uploaded_file.type
                            )
                        }
                    )

                if response.status_code == 200:

                    data = response.json()

                    transcript_text = data.get(
                        "transcript",
                        ""
                    )

                    st.success(
                        "✅ Transcription Completed"
                    )

                else:
                    st.error(response.text)

            except Exception as e:
                st.error(str(e))

# =====================================================
# YOUTUBE TAB
# =====================================================

with tab2:

    st.subheader("Transcribe YouTube Video")

    youtube_url = st.text_input(
        "Enter YouTube URL"
    )

    if st.button("🎥 Transcribe YouTube"):

        if youtube_url:

            try:

                with st.spinner(
                    "📥 Downloading and Transcribing..."
                ):

                    response = requests.post(
                        f"{BACKEND_URL}/youtube",
                        json={
                            "url": youtube_url
                        }
                    )

                if response.status_code == 200:

                    data = response.json()

                    transcript_text = data.get(
                        "transcript",
                        ""
                    )

                    st.success(
                        "✅ Transcription Completed"
                    )

                else:
                    st.error(response.text)

            except Exception as e:
                st.error(str(e))

        else:
            st.warning(
                "Please enter a YouTube URL."
            )

# =====================================================
# RESULTS
# =====================================================

if transcript_text:

    word_count = len(
        transcript_text.split()
    )

    char_count = len(
        transcript_text
    )

    estimated_minutes = max(
        1,
        round(word_count / 150)
    )

    st.markdown("---")

    st.subheader("📊 Meeting Analytics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{word_count}</div>
            <div class="metric-label">Words</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{char_count}</div>
            <div class="metric-label">Characters</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{estimated_minutes}</div>
            <div class="metric-label">Minutes</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")


    st.markdown("### 📝 Transcript")

    st.markdown(
        f"""
        <div style="
            background:#111827;
            padding:20px;
            border-radius:15px;
            line-height:1.8;
            font-size:16px;
            color:white;
        ">
        {transcript_text}
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            label="📥 Download Transcript",
            data=transcript_text,
            file_name="transcript.txt",
            mime="text/plain"
        )

    with col2:

        st.download_button(
            label="📄 Download Report",
            data=transcript_text,
            file_name="meeting_report.md",
            mime="text/markdown"
        )