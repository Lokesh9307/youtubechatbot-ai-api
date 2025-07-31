import os
import requests
import subprocess
import tempfile
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

SCRAPERAPI_KEY = "6a0f4c9d9a381c966b6dfe0c7ec35c70"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # export GROQ_API_KEY=your_key in terminal

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

def get_transcript_from_url(url: str) -> str:
    video_id = extract_video_id(url)

    # Try YouTubeTranscriptApi with proxy
    try:
        proxies = {
            "https": f"http://{SCRAPERAPI_KEY}@scraperapi.com:8001"
        }
        transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
        return " ".join([t['text'] for t in transcript])
    
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        print("Transcript not available. Falling back to Whisper...")
    
    except Exception as e:
        print(f"Transcript fetch error: {e}, using Whisper fallback.")

    # Fallback: Use Groq Whisper
    return run_whisper_transcription(url, video_id)

def run_whisper_transcription(url: str, video_id: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = os.path.join(tmpdir, f"{video_id}.mp3")

        # Download YouTube audio
        cmd = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", "mp3",
            "-o", audio_path,
            url
        ]
        subprocess.run(cmd, check=True)

        with open(audio_path, "rb") as audio_file:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                files={"file": audio_file},
                data={"model": "whisper-large-v3"}
            )

        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            raise Exception(f"Whisper transcription failed: {response.text}")
