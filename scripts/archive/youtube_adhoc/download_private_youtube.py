#!/usr/bin/env python3
"""
Download private YouTube videos with authentication and Chinese subtitles
"""

import os
import sys
from pathlib import Path
import yt_dlp
import argparse

def download_private_video(url, output_dir="data/input/videos", cookies_file=None):
    """
    Download a private YouTube video with Chinese subtitles

    Args:
        url: YouTube video URL
        output_dir: Output directory for video and subtitles
        cookies_file: Path to cookies file for authentication
    """

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',

        # Subtitle options - download Chinese subtitles
        'writesubtitles': True,
        'writeautomaticsub': True,  # Get auto-generated subtitles if no manual ones
        'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW'],  # All Chinese variants
        'subtitlesformat': 'vtt/srt/best',

        # Authentication options
        'username': None,  # Will be set if provided
        'password': None,  # Will be set if provided
        'cookiefile': cookies_file,  # Use cookies for authentication

        # Additional options
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'ignoreerrors': False,

        # Post-processing to embed subtitles
        'postprocessors': [{
            'key': 'FFmpegEmbedSubtitle',
            'already_have_subtitle': False,
        }],

        # Keep the subtitle files as well
        'keepvideo': True,
    }

    # Download the video
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading video from: {url}")
            print(f"Output directory: {output_path}")

            # Extract info first to check availability
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')

            print(f"Video title: {video_title}")

            # Check for available subtitles
            if 'subtitles' in info:
                print("Available subtitles:", list(info['subtitles'].keys()))
            if 'automatic_captions' in info:
                print("Available auto-captions:", list(info['automatic_captions'].keys()))

            # Now download
            ydl.download([url])

            print(f"\nDownload completed successfully!")
            print(f"Check {output_path} for the video and subtitle files")

    except Exception as e:
        print(f"Error downloading video: {e}")
        print("\nFor private videos, you need to provide authentication.")
        print("Options:")
        print("1. Export cookies from your browser (recommended)")
        print("2. Use OAuth authentication")
        raise

def export_cookies_instructions():
    """Print instructions for exporting cookies"""
    print("\n" + "="*60)
    print("HOW TO EXPORT COOKIES FOR PRIVATE VIDEO ACCESS:")
    print("="*60)
    print("\n1. Install a browser extension:")
    print("   - Chrome/Edge: 'Get cookies.txt LOCALLY' or 'EditThisCookie'")
    print("   - Firefox: 'cookies.txt'")
    print("\n2. Log in to YouTube in your browser")
    print("\n3. Go to the private video page")
    print("\n4. Use the extension to export cookies in Netscape format")
    print("\n5. Save as 'youtube_cookies.txt' in this directory")
    print("\n6. Run: poetry run python download_private_youtube.py --cookies youtube_cookies.txt --url <video_url>")
    print("="*60 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Download private YouTube videos with Chinese subtitles')
    parser.add_argument('--url', '-u', type=str,
                       default='https://youtu.be/iHAb48m7tOg',
                       help='YouTube video URL')
    parser.add_argument('--output', '-o', type=str,
                       default='data/input/videos',
                       help='Output directory')
    parser.add_argument('--cookies', '-c', type=str,
                       help='Path to cookies.txt file for authentication')
    parser.add_argument('--help-cookies', action='store_true',
                       help='Show instructions for exporting cookies')

    args = parser.parse_args()

    if args.help_cookies:
        export_cookies_instructions()
        sys.exit(0)

    # Check if cookies file exists
    if args.cookies:
        cookies_path = Path(args.cookies)
        if not cookies_path.exists():
            print(f"Error: Cookies file not found: {args.cookies}")
            export_cookies_instructions()
            sys.exit(1)
    else:
        print("Warning: No cookies file provided. This may fail for private videos.")
        print("Run with --help-cookies for instructions on how to export cookies.\n")

    # Download the video
    try:
        download_private_video(args.url, args.output, args.cookies)
    except Exception as e:
        print(f"\nFailed to download: {e}")
        if not args.cookies:
            print("\nTry providing a cookies file for authentication.")
            export_cookies_instructions()
        sys.exit(1)

if __name__ == "__main__":
    main()