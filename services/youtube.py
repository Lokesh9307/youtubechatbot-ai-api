import os
import requests
from urllib.parse import urlparse, parse_qs
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from utils.config import load_env

# Load environment variables
load_env()

# Get API keys from environment
SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not SCRAPERAPI_KEY:
    raise ValueError("SCRAPER_API_KEY is not set in the environment.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in the environment.")

# Proxy configuration
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
            return parse_qs(query.query).get('v', [None])[0]
        elif query.path.startswith('/embed/') or query.path.startswith('/v/'):
            return query.path.split('/')[2]
    raise ValueError("Invalid YouTube URL format.")


def download_audio(url: str, output_path="temp_audio.mp3") -> str:
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            raise Exception("No audio stream found for the video.")
        audio_stream.download(filename=output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Failed to download audio: {e}")


def transcribe_with_groq_whisper(audio_path: str) -> str:
    try:
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
            return response.json().get("text", "")
        else:
            raise Exception(f"Whisper transcription failed: {response.status_code} - {response.text}")

    except Exception as e:
        raise Exception(f"Groq Whisper API error: {e}")


def get_transcript_from_url(url: str) -> str:
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list(video_id, proxies=SCRAPERAPI_PROXY)

        try:
            # Attempt to get English transcript
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            # Fallback to any auto-generated language
            auto_langs = [t.language_code for t in transcript_list if t.is_generated]
            if not auto_langs:
                raise NoTranscriptFound("No auto-generated transcripts found.")
            transcript = transcript_list.find_transcript(auto_langs)

        transcript_text = " ".join([t.text for t in transcript.fetch()])
        return transcript_text

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, Exception) as e:
        print(f"[Fallback to Whisper] Transcript API failed: {e}")
        try:
            audio_path = download_audio(url)
            return transcribe_with_groq_whisper(audio_path)
        finally:
            if os.path.exists("temp_audio.mp3"):
                os.remove("temp_audio.mp3")
