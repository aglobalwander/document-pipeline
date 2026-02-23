#!/usr/bin/env python3
"""
Simplified YouTube fetcher - just get the video without subtitles first
"""

import yt_dlp
import os

def fetch_video_simple():
    url = 'https://www.youtube.com/watch?v=3uGXvdbL1ys&ab_channel=NintendoofAmerica'
    
    # Create output directory
    output_dir = 'data/output/youtube'
    os.makedirs(output_dir, exist_ok=True)
    
    # Simple configuration - video only first
    ydl_opts = {
        'format': 'best[height<=720]',  
        'outtmpl': f'{output_dir}/%(title)s_%(id)s.%(ext)s',
        'cookiesfrombrowser': ('chrome',),
        'writeinfojson': True,
        # Skip subtitle download for now
        'writesubtitles': False,
        'writeautomaticsub': False,
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
            print(f"Video ID: {info_dict.get('id', 'N/A')}")
            
            # List downloaded files
            print(f"\n📁 Files saved in: {output_dir}/")
            if os.path.exists(output_dir):
                for file in os.listdir(output_dir):
                    print(f"  - {file}")
                    
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    fetch_video_simple()