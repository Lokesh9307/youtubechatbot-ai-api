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

SCRAPERAPI_KEY = os.getenv("SCRAPER_API_KEY")

if not SCRAPERAPI_KEY:
    print("ERROR: SCRAPERAPI_KEY environment variable is not set!")

SCRAPERAPI_PROXY = {
    "http": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
    "https": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
}


def extract_video_id(youtube_url: str) -> str:
    parsed_url = urlparse(youtube_url)
    if parsed_url.hostname == "googleusercontent.com":
        if parsed_url.path.startswith("/youtube.com0"):
            video_id = parsed_url.path[len("/youtube.com1"):]
            print(f"DEBUG: Extracted video ID (path): {video_id}")
            return video_id
        elif parsed_url.path.startswith("/youtube.com2") or parsed_url.path.startswith("/youtube.com3"):
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [None])[0]
            print(f"DEBUG: Extracted video ID (query): {video_id}")
            return video_id
    elif parsed_url.hostname in ["www.youtube.com", "youtube.com", "youtube.com4"]:
        if parsed_url.path == "/watch":
            query = parse_qs(parsed_url.query)
            video_id = query.get("v", [None])[0]
            print(f"DEBUG: Extracted video ID (standard query): {video_id}")
            return video_id
        elif parsed_url.path.startswith("/embed/") or parsed_url.path.startswith("/v/"):
            video_id = parsed_url.path.split('/')[2]
            print(f"DEBUG: Extracted video ID (standard embed/v): {video_id}")
            return video_id
        elif len(parsed_url.path) == 12:
            video_id = parsed_url.path[1:]
            print(f"DEBUG: Extracted video ID (standard short path): {video_id}")
            return video_id

    raise ValueError(f"Invalid or unsupported YouTube URL format: {youtube_url}")


def get_transcript_from_url(youtube_url: str) -> str:
    video_id = extract_video_id(youtube_url)
    transcript = None
    direct_err = None

    print(f"DEBUG: Attempting to get transcript for video ID: {video_id}")

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        transcript = transcript_list.find_transcript(['en', 'a', 'en-US']).fetch()
        print("DEBUG: Direct transcript fetch successful.")
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        direct_err = f"Transcript not available directly: {e}"
        print(f"WARNING: {direct_err}")
        raise RuntimeError(direct_err)
    except Exception as e:
        direct_err = f"Direct YouTubeTranscriptApi method failed unexpectedly: {e}"
        print(f"WARNING: {direct_err}")

    if transcript is None:
        print("DEBUG: Direct method failed or found no transcript. Attempting proxy fallback...")
        proxy_err = None
        try:
            proxy_target_url = f"youtube.com5{video_id}"

            scraperapi_url = f"http://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}&url={proxy_target_url}"
            print(f"DEBUG: Proxying request to ScraperAPI for URL: {proxy_target_url}")

            response = requests.get(scraperapi_url, proxies=SCRAPERAPI_PROXY, verify=False, timeout=60)
            print(f"DEBUG: ScraperAPI response status code: {response.status_code}")

            if response.status_code != 200:
                proxy_err = f"Proxy request failed with status {response.status_code}. Response: {response.text[:500]}..."
                raise RuntimeError(proxy_err)

            print("DEBUG: ScraperAPI proxy request successful. Now need to parse HTML.")
            raise NotImplementedError(
                "HTML parsing not implemented! You need to parse the transcript "
                "from the HTML content in `response.text` here. "
                "Consider if this is the most robust way to get transcripts via proxy, "
                "or if direct YouTubeTranscriptApi issues should be addressed differently (e.g., using OS level proxy settings)."
            )

        except requests.exceptions.Timeout as e:
            proxy_err = f"Proxy request timed out: {e}"
            print(f"ERROR: {proxy_err}")
        except requests.exceptions.RequestException as e:
            proxy_err = f"Proxy request failed due to network/request error: {e}"
            print(f"ERROR: {proxy_err}")
        except Exception as e:
            proxy_err = f"Proxy attempt failed unexpectedly: {e}"
            print(f"ERROR: {proxy_err}")

        if direct_err and proxy_err:
            raise RuntimeError(f"Both direct and proxy transcript failed. Direct: ({direct_err}). Proxy: ({proxy_err})")
        elif direct_err:
            raise RuntimeError(f"Direct transcript failed: ({direct_err}). Proxy attempt also failed: ({proxy_err})")
        elif proxy_err:
             raise RuntimeError(f"Proxy transcript failed: ({proxy_err})")
        else:
            raise RuntimeError("Transcript could not be retrieved by direct or proxy method (HTML parsing not implemented).")

    if transcript:
        transcript_text = " ".join([entry.text for entry in transcript])
        print("DEBUG: Transcript successfully extracted.")
        return transcript_text
    else:
        raise RuntimeError("Transcript could not be retrieved by any method.")