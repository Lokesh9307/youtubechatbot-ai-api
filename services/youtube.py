import os
import requests
from urllib.parse import urlparse, parse_qs
from pytube import YouTube
from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from utils.config import load_env

load_env()

# ENV
SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Proxy config
SCRAPERAPI_PROXY = {
    "http": f"http://scraperapi.proxycrawl.com:8012/?api_key={SCRAPERAPI_KEY}&country=us",
    "https": f"http://scraperapi.proxycrawl.com:8012/?api_key={SCRAPERAPI_KEY}&country=us"
}

def extract_video_id(url: str) -> str:
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith('/embed/') or query.path.startswith('/v/'):
            return query.path.split('/')[2]
    raise ValueError("Invalid YouTube URL")

def download_audio(url: str, output_path="temp_audio.mp3") -> str:
    yt = YouTube(url)
    audio_stream = yt.streams.filter(only_audio=True).first()
    audio_stream.download(filename=output_path)
    return output_path

def transcribe_with_groq_whisper(audio_path: str) -> str:
    with open(audio_path, 'rb') as audio_file:
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}"
            },
            files={
                "file": (audio_path, audio_file, "audio/mpeg")
            },
            data={
                "model": "whisper-large-v3"
            }
        )

        if response.status_code == 200:
            return response.json()['text']
        else:
            raise Exception(f"Whisper transcription failed: {response.text}")

def get_transcript_from_url(url: str) -> str:
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list(video_id, proxies=SCRAPERAPI_PROXY)

        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            auto_langs = [t.language_code for t in transcript_list if t.is_generated]
            if not auto_langs:
                raise NoTranscriptFound("No auto-generated transcripts found.")
            transcript = transcript_list.find_transcript(auto_langs)

        transcript_text = " ".join([t.text for t in transcript.fetch()])
        return transcript_text

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, Exception) as e:
        print(f"[Fallback] Using Whisper because: {e}")
        try:
            audio_path = download_audio(url)
            return transcribe_with_groq_whisper(audio_path)
        finally:
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
