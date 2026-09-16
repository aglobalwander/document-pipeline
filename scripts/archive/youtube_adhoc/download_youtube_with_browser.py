#!/usr/bin/env python3
"""
Download YouTube videos (including private) using browser cookies
"""

import os
import sys
from pathlib import Path
import yt_dlp
import argparse

def download_with_browser_cookies(url, browser='chrome', output_dir="data/input/videos"):
    """
    Download YouTube video using cookies from your browser

    Args:
        url: YouTube video URL
        browser: Browser to extract cookies from (chrome, firefox, safari, edge)
        output_dir: Output directory
    """

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'outtmpl': str(output_path / '%(title)s.%(ext)s'),
        'format': 'best[ext=mp4]/best',

        # Use cookies from browser
        'cookiesfrombrowser': (browser, None),  # (browser_name, profile)

        # Subtitle options - download Chinese subtitles
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['zh', 'zh-Hans', 'zh-Hant', 'zh-CN', 'zh-TW', 'en'],
        'subtitlesformat': 'vtt/srt/best',

        # Keep subtitle files
        'keepvideo': True,

        # Verbose output
        'quiet': False,
        'no_warnings': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Extracting cookies from {browser} browser...")
            print(f"Downloading video from: {url}")
            print(f"Output directory: {output_path}\n")

            # Extract info first
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')

            print(f"Video title: {video_title}")

            # Check available subtitles
            if 'subtitles' in info:
                print("Manual subtitles available:", list(info['subtitles'].keys()))
            if 'automatic_captions' in info:
                print("Auto-generated subtitles available:", list(info['automatic_captions'].keys()))

            print("\nDownloading video and subtitles...")

            # Download
            ydl.download([url])

            print(f"\n✓ Download completed!")
            print(f"Files saved to: {output_path}/")

    except Exception as e:
        print(f"Error: {e}")
        print(f"\nMake sure you're logged into YouTube in {browser} browser")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos using browser cookies')
    parser.add_argument('--url', '-u', type=str,
                       default='https://youtu.be/iHAb48m7tOg',
                       help='YouTube video URL')
    parser.add_argument('--browser', '-b', type=str,
                       default='chrome',
                       choices=['chrome', 'firefox', 'safari', 'edge', 'brave', 'chromium'],
                       help='Browser to extract cookies from (default: chrome)')
    parser.add_argument('--output', '-o', type=str,
                       default='data/input/videos',
                       help='Output directory')

    args = parser.parse_args()

    print(f"Using cookies from {args.browser} browser")
    print("Make sure you're logged into YouTube in that browser\n")

    download_with_browser_cookies(args.url, args.browser, args.output)

if __name__ == "__main__":
    main()