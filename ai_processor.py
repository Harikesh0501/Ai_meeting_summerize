import whisper
from transformers import pipeline
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from database import save_meeting
import yake
import numpy as np

# Create a ThreadPool so heavy ML tasks don't block the FastAPI async server
executor = ThreadPoolExecutor(max_workers=2)

# Lazy-load models (loaded on first use to avoid blocking server startup)
whisper_model = None
summarizer = None
sentiment_analyzer = None
qa_model = None
speaker_encoder = None


def load_models():
    global whisper_model, summarizer, sentiment_analyzer
    if whisper_model is None:
        print("Loading Whisper Model (base)...")
        whisper_model = whisper.load_model("base")
    if summarizer is None:
        print("Loading Summarization Model (BART)...")
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    if sentiment_analyzer is None:
        print("Loading Sentiment Analysis Model...")
        sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )


def load_qa_model():
    global qa_model
    if qa_model is None:
        print("Loading Q&A Model (RoBERTa)...")
        qa_model = pipeline("question-answering", model="deepset/roberta-base-squad2")


def load_speaker_encoder():
    global speaker_encoder
    if speaker_encoder is None:
        print("Loading Speaker Encoder (Resemblyzer)...")
        from resemblyzer import VoiceEncoder
        speaker_encoder = VoiceEncoder()


# ─────────────────────────────────────────────
# Feature 1: Sentiment Analysis
# ─────────────────────────────────────────────
def analyze_sentiment(text: str) -> dict:
    """Analyze overall sentiment of the meeting transcript."""
    try:
        # Split into chunks (model has 512 token limit)
        chunk_size = 400
        words = text.split()
        chunks = [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

        if not chunks:
            return {"label": "NEUTRAL", "score": 0.5}

        # Analyze up to 10 chunks
        results = sentiment_analyzer(chunks[:10])

        # Aggregate scores
        pos_score = sum(r['score'] for r in results if r['label'] == 'POSITIVE')
        neg_score = sum(r['score'] for r in results if r['label'] == 'NEGATIVE')
        total = len(results)

        if pos_score >= neg_score:
            return {"label": "POSITIVE", "score": round(pos_score / total, 2)}
        else:
            return {"label": "NEGATIVE", "score": round(neg_score / total, 2)}
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
        return {"label": "NEUTRAL", "score": 0.5}


# ─────────────────────────────────────────────
# Feature 2: Keyword / Topic Extraction
# ─────────────────────────────────────────────
def extract_keywords(text: str, top_n: int = 10) -> list:
    """Extract key topics/phrases from transcript using YAKE."""
    try:
        kw_extractor = yake.KeywordExtractor(
            lan="en", n=2, top=top_n,
            dedupLim=0.7, windowsSize=1
        )
        keywords = kw_extractor.extract_keywords(text)
        # YAKE returns (keyword, score) — lower score = more relevant
        return [kw[0] for kw in keywords]
    except Exception as e:
        print(f"Keyword extraction error: {e}")
        return []


# ─────────────────────────────────────────────
# Feature 3: Speaker Diarization (Resemblyzer)
# ─────────────────────────────────────────────
def diarize_speakers(file_path: str, segments: list) -> list:
    """Identify different speakers using voice embeddings + spectral clustering."""
    try:
        load_speaker_encoder()
        from resemblyzer import preprocess_wav
        from spectralcluster import SpectralClusterer

        # Load and preprocess audio to 16kHz mono
        wav = preprocess_wav(file_path)
        sample_rate = 16000

        embeddings = []
        valid_indices = []

        for i, seg in enumerate(segments):
            start_sample = int(seg["start"] * sample_rate)
            end_sample = int(seg["end"] * sample_rate)
            segment_wav = wav[start_sample:end_sample]

            # Skip segments shorter than 0.5 seconds
            if len(segment_wav) < int(sample_rate * 0.5):
                continue

            embedding = speaker_encoder.embed_utterance(segment_wav)
            embeddings.append(embedding)
            valid_indices.append(i)

        if len(embeddings) < 2:
            # Only one speaker detected or too few segments
            return [0] * len(segments)

        # Spectral clustering to identify speakers
        clusterer = SpectralClusterer(min_clusters=2, max_clusters=6)
        labels = clusterer.predict(np.array(embeddings))

        # Map labels back to all segments (skipped ones get nearest label)
        full_labels = []
        valid_idx = 0
        for i in range(len(segments)):
            if i in valid_indices:
                full_labels.append(int(labels[valid_idx]))
                valid_idx += 1
            else:
                # Use previous speaker label or default to 0
                full_labels.append(full_labels[-1] if full_labels else 0)

        return full_labels

    except Exception as e:
        print(f"Speaker diarization error: {e}")
        # Fallback: all segments labeled as Speaker 1
        return [0] * len(segments)


# ─────────────────────────────────────────────
# Feature 10: Q&A Chatbot
# ─────────────────────────────────────────────
def answer_question_sync(transcript: str, question: str) -> dict:
    """Answer a question about the meeting transcript (extractive QA)."""
    load_qa_model()
    try:
        # Truncate transcript for QA model context window
        context = transcript[:4000]
        result = qa_model(question=question, context=context)
        return {
            "answer": result["answer"],
            "confidence": round(result["score"], 2)
        }
    except Exception as e:
        print(f"QA error: {e}")
        return {"answer": "Could not find an answer.", "confidence": 0.0}


async def answer_question(transcript: str, question: str) -> dict:
    """Async wrapper for Q&A pipeline."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, answer_question_sync, transcript, question)


# ─────────────────────────────────────────────
# Existing: Action Items Extraction
# ─────────────────────────────────────────────
def extract_action_items(transcript: str) -> list[str]:
    action_items = []
    sentences = transcript.split('. ')
    keywords = ["need to", "must", "should", "will", "action", "task", "todo", "assign"]
    for sentence in sentences:
        if any(kw in sentence.lower() for kw in keywords):
            action_items.append(sentence.strip() + ".")
    return action_items


# ─────────────────────────────────────────────
# Main ML Pipeline (runs all features)
# ─────────────────────────────────────────────
def run_ml_pipeline(file_path: str):
    """Synchronous heavy ML task — runs Whisper + all analysis."""
    # Ensure core models are loaded
    load_models()

    # ── Step 1: Transcription ──
    print(f"Transcribing audio: {file_path}")
    transcript_result = whisper_model.transcribe(file_path, task="translate")

    # ── Step 2: Speaker Diarization ──
    print("Running speaker diarization...")
    speaker_labels = diarize_speakers(file_path, transcript_result["segments"])

    # ── Step 3: Build transcript with speaker labels + timestamps ──
    transcript_segments = []
    for i, segment in enumerate(transcript_result["segments"]):
        start = segment["start"]
        end = segment["end"]
        text = segment["text"].strip()
        start_fmt = f"{int(start//60):02d}:{int(start%60):02d}"
        end_fmt = f"{int(end//60):02d}:{int(end%60):02d}"
        speaker_num = speaker_labels[i] + 1 if i < len(speaker_labels) else 1
        speaker = f"Speaker {speaker_num}"
        transcript_segments.append(f"[{speaker}] [{start_fmt} - {end_fmt}] {text}")

    transcript = "\n".join(transcript_segments)
    raw_text = transcript_result["text"]

    # ── Step 4: Audio Duration ──
    duration_seconds = 0
    if transcript_result["segments"]:
        duration_seconds = round(transcript_result["segments"][-1]["end"])

    # ── Step 5: Summarization ──
    print("Summarizing text...")
    truncated_transcript = raw_text[:4000]
    word_count = len(truncated_transcript.split())
    max_length = min(150, max(30, word_count // 2))

    summary = ""
    if word_count > 20:
        summary_result = summarizer(
            truncated_transcript,
            max_length=max_length,
            min_length=int(max_length * 0.3),
            do_sample=False
        )
        summary = summary_result[0]['summary_text']
    else:
        summary = "Audio too short to generate a meaningful summary."

    # ── Step 6: Sentiment Analysis ──
    print("Analyzing sentiment...")
    sentiment = analyze_sentiment(raw_text)

    # ── Step 7: Keyword Extraction ──
    print("Extracting keywords...")
    keywords = extract_keywords(raw_text)

    # ── Step 8: Action Items ──
    action_items = extract_action_items(raw_text)

    return transcript, summary, action_items, sentiment, keywords, duration_seconds


async def process_audio_task(file_path: str, filename: str):
    """Async wrapper for ML pipeline to safely integrate with FastAPI and Motor."""
    loop = asyncio.get_running_loop()
    try:
        # Run full ML pipeline in background thread
        transcript, summary, action_items, sentiment, keywords, duration_seconds = \
            await loop.run_in_executor(executor, run_ml_pipeline, file_path)

        print("ML Pipeline completed. Saving results...")
        await save_meeting({
            "filename": filename,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
            "sentiment": sentiment,
            "keywords": keywords,
            "duration_seconds": duration_seconds,
            "status": "completed"
        })
        print("Successfully saved results.")

    except Exception as e:
        print(f"Error processing audio: {e}")
        await save_meeting({
            "filename": filename,
            "status": "failed",
            "error": str(e)
        })
    finally:
        # Cleanup temp file
        if os.path.exists(file_path):
            os.remove(file_path)
            print("Removed temporary audio file.")
