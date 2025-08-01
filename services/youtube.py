import os
import requests
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from utils.config import load_env
load_env()

# Load API key from environment
SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")

# ScraperAPI proxy config
SCRAPERAPI_PROXY = {
    "http": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
    "https": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
}


def extract_video_id(youtube_url: str) -> str:
    """Extract the video ID from a YouTube URL."""
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        query = parse_qs(parsed_url.query)
        return query.get("v", [None])[0]
    raise ValueError("Invalid YouTube URL format")


def get_transcript_from_url(youtube_url: str) -> str:
    """Get transcript using YouTubeTranscriptApi or fallback to ScraperAPI proxy."""
    video_id = extract_video_id(youtube_url)
    try:
        # Try without proxy first
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(['en']).fetch()
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        raise RuntimeError(f"Transcript not available: {e}")
    except Exception as e:
        print(f"[Proxy fallback] Direct method failed: {e}")
        # Retry with proxy using requests and http API fallback
        try:
            url = f"http://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url=https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url, proxies=SCRAPERAPI_PROXY, verify=False)
            if response.status_code != 200:
                raise RuntimeError("Proxy request failed")

            # If needed: parse transcript from page source manually here
            raise NotImplementedError("HTML parsing not implemented")

        except Exception as proxy_err:
            raise RuntimeError(f"Both direct and proxy transcript failed: {proxy_err}")

    # Join transcript text
    transcript_text = " ".join([entry.text for entry in transcript])
    return transcript_text
