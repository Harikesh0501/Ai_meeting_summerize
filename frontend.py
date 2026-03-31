import streamlit as st
import requests
from streamlit_autorefresh import st_autorefresh
from deep_translator import GoogleTranslator

st.set_page_config(page_title="AI Meeting Summarizer", page_icon="🎙️", layout="wide")

st.title("🎙️ AI Meeting Summarizer")
st.markdown("Upload your meeting audio to automatically generate a **transcript**, **summary**, and extract **action items**.")

# Config
BACKEND_URL = "http://localhost:8000"  # temporarily using local backend for fast testing
st_autorefresh(interval=10000, limit=200, key="data_refresh")

# ─────────────────────────────────────────────
# Sidebar: Upload File
# ─────────────────────────────────────────────
st.sidebar.header("📁 Upload Audio")
uploaded_file = st.sidebar.file_uploader("Select an audio file", type=["mp3", "wav", "m4a", "mp4"])

if uploaded_file is not None:
    st.sidebar.audio(uploaded_file, format='audio/wav')
    if st.sidebar.button("Generate Summary & Notes"):
        with st.spinner("Processing in background..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            try:
                response = requests.post(f"{BACKEND_URL}/upload-audio/", files=files)
                if response.status_code == 200:
                    st.sidebar.success("✅ Uploaded! AI is working in the background.")
                    st.sidebar.info("Refresh the dashboard in a few moments to see your notes.")
                else:
                    st.sidebar.error("Server Error!")
            except Exception as e:
                st.sidebar.error(f"Connection Failed: {e}")

# ─────────────────────────────────────────────
# Sidebar: Process from URL (YouTube, etc.)
# ─────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.header("🔗 Process from URL")
url_input = st.sidebar.text_input(
    "Paste a YouTube or video URL:",
    placeholder="https://www.youtube.com/watch?v=...",
    key="url_input"
)

if st.sidebar.button("🚀 Process URL", key="process_url_btn"):
    if url_input and url_input.strip():
        with st.spinner("Sending URL for processing..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/process-url/",
                    json={"url": url_input.strip()},
                    timeout=10
                )
                if response.status_code == 200:
                    st.sidebar.success("✅ URL received! AI is downloading & processing in the background.")
                    st.sidebar.info("⏳ This may take a few minutes depending on video length. Dashboard will auto-refresh.")
                else:
                    st.sidebar.error(f"Server Error: {response.text}")
            except Exception as e:
                st.sidebar.error(f"Connection Failed: {e}")
    else:
        st.sidebar.warning("⚠️ Please paste a valid URL first.")

st.sidebar.caption("Supports: YouTube, Instagram, Twitter, Facebook, and 1000+ sites")

# ─────────────────────────────────────────────
# Sidebar: Language Translator
# ─────────────────────────────────────────────
LANGUAGES = {
    "English": "en",
    "Gujarati (ગુજરાતી)": "gu",
    "Hindi (हिंदी)": "hi",
    "Marathi (मराठी)": "mr",
    "Spanish (Español)": "es",
    "French (Français)": "fr",
    "German (Deutsch)": "de"
}
st.sidebar.markdown("---")
st.sidebar.header("🌐 Output Language")
selected_lang_name = st.sidebar.selectbox("Translate dashboard to:", list(LANGUAGES.keys()))
target_lang_code = LANGUAGES[selected_lang_name]


@st.cache_data(show_spinner=False)
def translate_text(text: str, target_lang: str):
    if not text or target_lang == "en":
        return text
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        chunk_size = 4500
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        translated_chunks = [translator.translate(chunk) for chunk in chunks]
        return "".join(translated_chunks)
    except Exception as e:
        st.error(f"Translation error: {e}")
        return text


def format_duration(seconds):
    """Format seconds into human-readable duration."""
    if not seconds:
        return "Unknown"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} min {secs} sec"
    return f"{secs} sec"


# ─────────────────────────────────────────────
# Main Dashboard
# ─────────────────────────────────────────────
st.header("📊 Recent Meetings Dashboard")

if st.button("🔄 Refresh Data manually"):
    st.rerun()


def display_meeting(idx, m, prefix):
    """Display a single meeting inside an expander with all features."""
    with st.expander(f"📝 {m.get('filename', 'Unknown File')} — {m.get('status', 'Unknown Status').upper()}"):

        if m.get('status') == 'completed':

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Info Bar: Date | Duration | Sentiment
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            col_date, col_dur, col_sent = st.columns(3)

            # Date
            created_at = m.get('created_at', '')
            if created_at:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at)
                    formatted_date = dt.strftime("%d %b %Y, %I:%M %p")
                except Exception:
                    formatted_date = str(created_at)
            else:
                formatted_date = "Unknown"

            with col_date:
                st.markdown(f"📅 **Date:** {formatted_date}")

            # Duration
            with col_dur:
                duration = m.get('duration_seconds', 0)
                st.markdown(f"⏱️ **Duration:** {format_duration(duration)}")

            # Sentiment
            with col_sent:
                sentiment = m.get('sentiment', {})
                label = sentiment.get('label', 'NEUTRAL')
                score = sentiment.get('score', 0)
                pct = int(score * 100)
                if label == "POSITIVE":
                    st.markdown(f"😊 **Sentiment:** :green[{label}] ({pct}%)")
                elif label == "NEGATIVE":
                    st.markdown(f"😟 **Sentiment:** :red[{label}] ({pct}%)")
                else:
                    st.markdown(f"😐 **Sentiment:** :orange[{label}] ({pct}%)")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Keywords / Key Topics
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            keywords = m.get('keywords', [])
            if keywords:
                keyword_tags = "  ".join([f"`{kw}`" for kw in keywords])
                st.markdown(f"🔑 **Key Topics:** {keyword_tags}")

            st.markdown("---")

            # ── Translation ──
            raw_summary = m.get('summary', 'No summary available.')
            raw_transcript = m.get('transcript', 'No transcript found.')
            raw_action_items = m.get('action_items', [])

            with st.spinner("Translating content..." if target_lang_code != "en" else "Loading native content..."):
                display_summary = translate_text(raw_summary, target_lang_code)
                display_transcript = translate_text(raw_transcript, target_lang_code)
                display_action_items = [translate_text(item, target_lang_code) for item in raw_action_items]

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # AI Summary
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.subheader("📌 AI Summary")
            st.success(display_summary)

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Action Items
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.subheader("🎯 Action Items")
            if display_action_items:
                for item in display_action_items:
                    st.write(f"- {item}")
            else:
                st.write("No action items detected.")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Transcript with Speaker Labels
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.subheader("📝 Full Transcript")
            st.text_area(
                "Transcript Text", display_transcript,
                height=200, key=f"trans_{prefix}_{idx}_{target_lang_code}"
            )

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Q&A Chatbot
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.markdown("---")
            st.subheader("🤖 Ask AI about this Meeting")
            question = st.text_input(
                "Type your question:",
                key=f"qa_input_{prefix}_{idx}",
                placeholder="e.g., What was discussed about the budget?"
            )

            if st.button("🔍 Ask AI", key=f"qa_btn_{prefix}_{idx}"):
                if question:
                    with st.spinner("AI is thinking..."):
                        try:
                            qa_response = requests.post(
                                f"{BACKEND_URL}/meetings/{m.get('_id')}/ask",
                                json={"question": question},
                                timeout=30
                            )
                            if qa_response.status_code == 200:
                                result = qa_response.json()
                                st.session_state[f"qa_answer_{prefix}_{idx}"] = result
                            else:
                                st.error("Could not get an answer from AI.")
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.warning("Please type a question first.")

            # Display stored answer
            answer_key = f"qa_answer_{prefix}_{idx}"
            if answer_key in st.session_state:
                result = st.session_state[answer_key]
                confidence = result.get('confidence', 0)
                st.info(f"**Answer:** {result.get('answer', 'No answer found.')}")
                st.caption(f"Confidence: {int(confidence * 100)}%")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # Action Buttons
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🗑️ Delete", key=f"del_{prefix}_{idx}"):
                    del_res = requests.delete(f"{BACKEND_URL}/meetings/{m.get('_id')}")
                    if del_res.status_code == 200:
                        st.rerun()
                        st.success("Deleted!")
            with col2:
                st.download_button(
                    "📥 Download Summary", display_summary,
                    file_name=f"summary_{m.get('filename')}.txt",
                    key=f"dl_sum_{prefix}_{idx}"
                )
            with col3:
                st.download_button(
                    "📥 Download Transcript", display_transcript,
                    file_name=f"transcript_{m.get('filename')}.txt",
                    key=f"dl_trans_{prefix}_{idx}"
                )

        elif m.get('status') == 'failed':
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("🗑️ Delete Failed", key=f"delf_{prefix}_{idx}"):
                    requests.delete(f"{BACKEND_URL}/meetings/{m.get('_id')}")
                    st.rerun()
            with col2:
                st.error(f"Processing failed: {m.get('error')}")
        else:
            st.warning("Currently processing... please wait and refresh.")


# ─────────────────────────────────────────────
# Fetch and Display Meetings
# ─────────────────────────────────────────────
try:
    meetings_response = requests.get(f"{BACKEND_URL}/meetings?limit=100", timeout=5)

    if meetings_response.status_code == 200:
        meetings = meetings_response.json()

        tab1, tab2 = st.tabs(["🎙️ Recent Uploads", "📜 Full History"])

        with tab1:
            recent_meetings = meetings[:1]
            if not recent_meetings:
                st.info("No meetings found. Upload an audio file to get started!")

            for idx, m in enumerate(recent_meetings):
                display_meeting(idx, m, "t1")

        with tab2:
            search_query = st.text_input("🔍 Search History (by filename, summary, or transcript):")
            history_meetings = meetings

            if search_query:
                query = search_query.lower()
                history_meetings = [
                    m for m in meetings
                    if query in str(m.get('filename', '')).lower()
                    or query in str(m.get('summary', '')).lower()
                    or query in str(m.get('transcript', '')).lower()
                    or any(query in kw.lower() for kw in m.get('keywords', []))
                ]

            if not history_meetings:
                st.info("No historical meetings found.")

            for idx, m in enumerate(history_meetings):
                display_meeting(idx, m, "t2")

    else:
        st.error(f"Could not load meetings. Status code: {meetings_response.status_code}")
except Exception as e:
    st.error(f"Backend Server might be down or not running. Please start the FastAPI backend on port 8000. Error: {e}")
