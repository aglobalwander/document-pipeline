#!/usr/bin/env python3
"""
Extract Chinese subtitles from YouTube video using youtube-transcript-api
"""

import json
import sys
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api import Transcript
import re

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?]*)',
        r'(?:youtube\.com\/embed\/)([^&\n?]*)',
        r'(?:youtube\.com\/v\/)([^&\n?]*)'
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_chinese_subtitles(video_id):
    """
    Get Chinese subtitles from YouTube video

    Args:
        video_id: YouTube video ID

    Returns:
        List of subtitle entries with text and timestamps
    """
    try:
        # Initialize the API
        api = YouTubeTranscriptApi()

        # List available transcripts
        print(f"Fetching transcript list for video: {video_id}")
        transcript_list = api.list(video_id)

        # Print available transcripts
        print("\nAvailable transcripts:")
        for transcript in transcript_list:
            print(f"  - {transcript.language} ({transcript.language_code})")
            if transcript.is_generated:
                print(f"    (auto-generated)")

        # Try to find Chinese transcript
        chinese_codes = ['zh', 'zh-CN', 'zh-Hans', 'zh-Hant', 'zh-TW', 'zh-HK']

        for code in chinese_codes:
            try:
                print(f"\nTrying to find transcript with language code: {code}")
                transcript = transcript_list.find_transcript([code])
                print(f"✓ Found Chinese transcript: {code}")
                subtitles = transcript.fetch()
                print(f"✓ Successfully fetched {len(subtitles)} subtitle entries")
                return subtitles
            except Exception as e:
                print(f"  - No transcript found for {code}: {e}")
                continue

        # If no Chinese transcript, try to translate from English
        print("\nNo Chinese transcript found. Trying to translate from English...")
        try:
            # Find English transcript
            english_transcript = transcript_list.find_transcript(['en'])

            # Check if it's translatable to Chinese
            if 'zh' in english_transcript.translation_languages or 'zh-Hans' in english_transcript.translation_languages:
                print("Translating English transcript to Chinese...")
                chinese_transcript = english_transcript.translate('zh-Hans')
                subtitles = chinese_transcript.fetch()
                print(f"✓ Successfully translated and fetched {len(subtitles)} subtitle entries")
                return subtitles
            else:
                print("English transcript cannot be translated to Chinese")
        except Exception as e:
            print(f"Could not translate English transcript: {e}")

        # Fallback: return English subtitles
        print("\nFallback: Trying to get English subtitles...")
        try:
            transcript = transcript_list.find_transcript(['en'])
            subtitles = transcript.fetch()
            print(f"✓ Successfully fetched {len(subtitles)} English subtitle entries")
            return subtitles
        except Exception as e:
            print(f"Could not get English subtitles: {e}")

        return None

    except TranscriptsDisabled:
        print("Error: Transcripts are disabled for this video")
        return None
    except NoTranscriptFound:
        print("Error: No transcripts found for this video")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def save_subtitles(subtitles, output_path, format='srt'):
    """
    Save subtitles to file

    Args:
        subtitles: List of subtitle entries
        output_path: Output file path
        format: Output format ('srt', 'vtt', 'txt', 'json')
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == 'srt':
        # Save as SRT format
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, entry in enumerate(subtitles, 1):
                start = format_timestamp(entry['start'], 'srt')
                end = format_timestamp(entry['start'] + entry['duration'], 'srt')
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{entry['text']}\n\n")
        print(f"✓ Saved as SRT: {output_path}")

    elif format == 'vtt':
        # Save as WebVTT format
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            for entry in subtitles:
                start = format_timestamp(entry['start'], 'vtt')
                end = format_timestamp(entry['start'] + entry['duration'], 'vtt')
                f.write(f"{start} --> {end}\n")
                f.write(f"{entry['text']}\n\n")
        print(f"✓ Saved as VTT: {output_path}")

    elif format == 'txt':
        # Save as plain text
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in subtitles:
                f.write(f"{entry['text']}\n")
        print(f"✓ Saved as TXT: {output_path}")

    elif format == 'json':
        # Save as JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved as JSON: {output_path}")

def format_timestamp(seconds, format_type):
    """Convert seconds to timestamp format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if format_type == 'srt':
        # SRT format: 00:00:00,000
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
    else:
        # VTT format: 00:00:00.000
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def main():
    # Default video URL
    url = "https://youtu.be/iHAb48m7tOg"

    if len(sys.argv) > 1:
        url = sys.argv[1]

    # Extract video ID
    video_id = extract_video_id(url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {url}")
        sys.exit(1)

    print(f"Video ID: {video_id}")
    print(f"URL: {url}\n")

    # Get Chinese subtitles
    subtitles = get_chinese_subtitles(video_id)

    if subtitles:
        # Save in multiple formats
        base_path = Path("data/input/videos/SAS_Belonging_Video_chinese")

        save_subtitles(subtitles, f"{base_path}.srt", format='srt')
        save_subtitles(subtitles, f"{base_path}.vtt", format='vtt')
        save_subtitles(subtitles, f"{base_path}.txt", format='txt')
        save_subtitles(subtitles, f"{base_path}.json", format='json')

        # Print first few lines as preview
        print("\n--- Preview of Chinese subtitles ---")
        for entry in subtitles[:5]:
            print(f"[{entry['start']:.2f}s] {entry['text']}")
        print("...")
    else:
        print("\nFailed to extract Chinese subtitles")
        sys.exit(1)

if __name__ == "__main__":
    main()