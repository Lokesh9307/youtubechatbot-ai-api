import os
import requests
import tempfile
from urllib.parse import urlparse, parse_qs
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from utils.config import load_env

# Load environment variables
load_env()

# Get API keys
SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Validate environment
if not SCRAPERAPI_KEY:
    raise ValueError("SCRAPER_API_KEY is missing in environment.")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in environment.")

# Proxy configuration
SCRAPERAPI_PROXY = {
    "http": f"http://scraperapi.proxycrawl.com:8012/?api_key={SCRAPERAPI_KEY}&country=us",
    "https": f"http://scraperapi.proxycrawl.com:8012/?api_key={SCRAPERAPI_KEY}&country=us"
}


def extract_video_id(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed_url.path == '/watch':
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.path.startswith('/embed/') or parsed_url.path.startswith('/v/'):
            return parsed_url.path.split('/')[2]
    raise ValueError("Invalid YouTube URL format.")


def download_audio(url: str) -> str:
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True).first()
        if not audio_stream:
            raise Exception("No audio stream found.")
        
        # Use a temporary file to avoid overwrite or leftover issues
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_stream.download(filename=temp_file.name)
        return temp_file.name
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
                    "file": (os.path.basename(audio_path), audio_file, "audio/mpeg")
                },
                data={
                    "model": "whisper-large-v3"
                }
            )

        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            raise Exception(f"Whisper failed: {response.status_code} - {response.text}")

    except Exception as e:
        raise Exception(f"Groq Whisper API error: {e}")


def get_transcript_from_url(url: str) -> str:
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list(video_id, proxies=SCRAPERAPI_PROXY)

        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            auto_langs = [t.language_code for t in transcript_list if t.is_generated]
            if not auto_langs:
                raise NoTranscriptFound("No generated transcript found.")
            transcript = transcript_list.find_transcript(auto_langs)

        return " ".join([entry.text for entry in transcript.fetch()])

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, Exception) as e:
        print(f"[Fallback] Transcript failed, switching to Whisper: {e}")
        audio_path = None
        try:
            audio_path = download_audio(url)
            return transcribe_with_groq_whisper(audio_path)
        finally:
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
