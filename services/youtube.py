from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from urllib.parse import urlparse, parse_qs

def extract_video_id(url: str) -> str:
    query = urlparse(url)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            return parse_qs(query.query)['v'][0]
        elif query.path.startswith('/embed/'):
            return query.path.split('/')[2]
        elif query.path.startswith('/v/'):
            return query.path.split('/')[2]
    raise ValueError("Invalid YouTube URL")

def get_transcript_from_url(url: str) -> str:
    try:
        video_id = extract_video_id(url)
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        # Try English first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            # Try auto-generated transcripts in any language
            transcript = transcript_list.find_transcript([t.language_code for t in transcript_list if t.is_generated])

        transcript_text = " ".join([t.text for t in transcript.fetch()])
        return transcript_text

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        raise Exception("Transcript not available. Use Whisper as fallback.")
    except Exception as e:
        raise Exception(f"Unexpected error while getting transcript: {str(e)}")
