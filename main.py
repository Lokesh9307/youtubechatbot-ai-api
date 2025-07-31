from fastapi import FastAPI, Request
from pydantic import BaseModel
from services.youtube import get_transcript_from_url
from services.indexer import build_index, query_index
from utils.config import load_env
import uvicorn
import os

app = FastAPI()

load_env()

class YouTubeRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    url: str
    question: str

@app.post("/extract_transcript")
def extract_transcript(data: YouTubeRequest):
    transcript = get_transcript_from_url(data.url)
    return {"transcript": transcript}

@app.post("/chat")
def chat_with_video(data: ChatRequest):
    transcript = get_transcript_from_url(data.url)
    index = build_index(transcript)
    response = query_index(index, data.question)
    return {"answer": response}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=False)