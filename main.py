from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import uvicorn
from database import (
    connect_to_mongo, close_mongo_connection,
    get_meetings as fetch_meetings,
    delete_meeting as remove_meeting,
    get_meeting_by_id
)
from ai_processor import process_audio_task, answer_question


class QuestionRequest(BaseModel):
    question: str


@asynccontextmanager
async def lifespan(app):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="AI Meeting Summarizer API", lifespan=lifespan)

# Setup CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Summarizer API!"}


@app.post("/upload-audio/")
async def upload_audio(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Save file temporarily
    file_location = f"temp_{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # Process audio in background (Whisper + all ML features)
    background_tasks.add_task(process_audio_task, file_location, file.filename)

    return {"message": "File uploaded successfully, processing started in the background."}


@app.get("/meetings/")
async def get_meetings_endpoint(limit: int = 100):
    meetings = await fetch_meetings(limit=limit)
    return meetings


@app.delete("/meetings/{meeting_id}")
async def delete_meeting_endpoint(meeting_id: str):
    success = await remove_meeting(meeting_id)
    if success:
        return {"message": "Meeting deleted successfully."}
    raise HTTPException(status_code=404, detail="Meeting not found or failed to delete.")


@app.post("/meetings/{meeting_id}/ask")
async def ask_question_endpoint(meeting_id: str, request: QuestionRequest):
    """Q&A Chatbot — ask questions about a specific meeting's transcript."""
    meeting = await get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found.")
    if meeting.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Meeting is not yet processed.")

    transcript = meeting.get("transcript", "")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript available.")

    result = await answer_question(transcript, request.question)
    return result


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
