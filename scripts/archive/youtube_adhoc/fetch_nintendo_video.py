#!/usr/bin/env python3
"""
Simple script to fetch the Nintendo Switch 2 video with proper browser cookies
"""

import yt_dlp
import tempfile
import os
import json

def fetch_nintendo_video():
    url = 'https://www.youtube.com/watch?v=3uGXvdbL1ys&ab_channel=NintendoofAmerica'
    
    # Create output directory
    output_dir = 'data/output/youtube'
    os.makedirs(output_dir, exist_ok=True)
    
    # Configuration for yt-dlp with Chrome cookies
    ydl_opts = {
        'format': 'best[height<=720]',  # Download decent quality
        'outtmpl': f'{output_dir}/%(title)s_%(id)s.%(ext)s',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'cookiesfrombrowser': ('chrome',),  # Use Chrome cookies
        'writeinfojson': True,  # Save metadata
    }
    
    print(f"Fetching: {url}")
    print(f"Output directory: {output_dir}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            
            print("\n✅ Successfully downloaded!")
            print(f"Title: {info_dict.get('title', 'N/A')}")
            print(f"Duration: {info_dict.get('duration', 'N/A')} seconds")
            print(f"Uploader: {info_dict.get('uploader', 'N/A')}")
            
            # List downloaded files
            print(f"\n📁 Files saved in: {output_dir}/")
            for file in os.listdir(output_dir):
                if info_dict.get('id', '') in file:
                    print(f"  - {file}")
                    
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    fetch_nintendo_video()