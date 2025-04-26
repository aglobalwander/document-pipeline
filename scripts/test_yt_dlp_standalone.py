import yt_dlp
import sys
import os

# Define a test YouTube URL
# Using a different test video URL
youtube_url = "https://www.youtube.com/watch?v=CdRzrYAqdnI"

# Define download options
# We'll download the best video and audio and merge them
ydl_opts = {
    'format': 'bestvideo+bestaudio/best',
    'merge_output_format': 'mp4',
    'outtmpl': os.path.join(os.path.dirname(__file__), 'downloaded_video.%(ext)s'), # Save to scripts directory
    'verbose': True, # Enable verbose output for debugging
    'cookiesfrombrowser': 'chrome:Default', # Load cookies from Chrome with default profile
}

print(f"Attempting to download video from: {youtube_url}")

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(youtube_url, download=True)
        print("\nDownload successful!")
        print(f"Title: {info_dict.get('title', 'N/A')}")
        print(f"Uploader: {info_dict.get('uploader', 'N/A')}")
        print(f"Duration: {info_dict.get('duration_string', 'N/A')}")

except Exception as e:
    print(f"\nAn error occurred during yt-dlp download: {e}")
    sys.exit(1)

sys.exit(0)