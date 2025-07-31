from youtube_transcript_api import YouTubeTranscriptApi

video_id = "WwoItTk4BvI"
ytt_api = YouTubeTranscriptApi()
transcript_list = ytt_api.list(video_id)
transcript = transcript_list.find_transcript(['en'])

# Access attributes like `.text` instead of `["text"]`
text = " ".join([t.text for t in transcript.fetch()])

print(text)
