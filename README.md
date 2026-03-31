# 🎙️ AI Meeting Summarizer

An AI-powered meeting analysis tool that automatically generates **transcripts**, **summaries**, **action items**, and more from audio files or video URLs (YouTube, Instagram, etc.).

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎙️ Audio Transcription | Whisper AI for accurate speech-to-text (supports 90+ languages → English) |
| 📝 AI Summary | BART-based summarization of meeting content |
| 🎯 Action Items | Auto-extract tasks, deadlines, and assignments |
| 👥 Speaker Diarization | Identify different speakers using voice embeddings |
| 😊 Sentiment Analysis | Analyze overall meeting tone (Positive/Negative/Neutral) |
| 🔑 Keyword Extraction | YAKE-based key topic/phrase extraction |
| 🤖 Q&A Chatbot | Ask questions about any meeting transcript |
| 🌐 Multi-Language | Translate dashboard to Gujarati, Hindi, Marathi, Spanish, French, German |
| 🔗 YouTube/URL Support | Paste any YouTube/video URL → auto-download & analyze |
| 🔍 Search & Filter | Search meetings by filename, summary, or transcript |
| 📥 Download | Export transcript and summary as text files |
| 🗑️ Delete | Remove meetings from dashboard |

## 🛠️ Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Frontend:** Streamlit
- **AI Models:** OpenAI Whisper, Facebook BART, DistilBERT, RoBERTa
- **Database:** MongoDB Atlas (Motor async driver)
- **Audio Download:** yt-dlp (1000+ sites supported)
- **Translation:** Google Translate (deep-translator)
- **Speaker ID:** Resemblyzer + Spectral Clustering

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- FFmpeg (included as `ffmpeg.exe` for Windows)
- MongoDB Atlas connection string

### Installation

```bash
# Clone the repository
git clone https://github.com/Harikesh0501/ai_meeting_summarizer.git
cd ai_meeting_summarizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:
```
MONGO_URI=your_mongodb_atlas_connection_string
```

### Run Locally

```bash
# Terminal 1: Start Backend
python main.py

# Terminal 2: Start Frontend
streamlit run frontend.py
```

- Backend API: http://localhost:8000
- Frontend Dashboard: http://localhost:8501

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload-audio/` | Upload audio file for processing |
| POST | `/process-url/` | Process audio from YouTube/video URL |
| GET | `/meetings/` | Get all processed meetings |
| DELETE | `/meetings/{id}` | Delete a meeting |
| POST | `/meetings/{id}/ask` | Ask Q&A about a meeting |

## 🌐 Deployment

### Streamlit Cloud
1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Set `frontend.py` as the main file
5. Add `MONGO_URI` in Streamlit secrets

### Hugging Face Spaces
1. Push code to Hugging Face repo
2. Configure as Streamlit app
3. Add secrets in Space settings

## 📄 License

MIT License
