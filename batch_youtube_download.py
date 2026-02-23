#!/usr/bin/env python3
"""
Batch YouTube downloader for multiple videos
"""

import yt_dlp
import os
from pathlib import Path

def batch_download_youtube():
    # List of URLs to download
    urls = [
        "https://www.youtube.com/watch?v=5sMBhDv4sik"
    ]
    
    # Create output directory
    output_dir = Path('data/output/youtube')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuration for yt-dlp
    ydl_opts = {
        'format': 'best[height<=720]',  # Download decent quality
        'outtmpl': str(output_dir / '%(title)s_%(id)s.%(ext)s'),
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'subtitlesformat': 'vtt/best',  # Prefer VTT format
        'cookiesfrombrowser': ('chrome',),  # Use Chrome cookies
        'writeinfojson': True,  # Save metadata
        'ignoreerrors': True,  # Continue on errors
        'skip_download': False,  # Download the video
    }
    
    print(f"📥 Starting batch download of {len(urls)} videos")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print("=" * 60)
    
    successful_downloads = []
    failed_downloads = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                
                title = info_dict.get('title', 'Unknown Title')
                duration = info_dict.get('duration', 'Unknown')
                uploader = info_dict.get('uploader', 'Unknown')
                video_id = info_dict.get('id', 'Unknown')
                
                print(f"✅ Downloaded: {title}")
                print(f"   Duration: {duration}s | Uploader: {uploader} | ID: {video_id}")
                
                successful_downloads.append({
                    'url': url,
                    'title': title,
                    'id': video_id,
                    'uploader': uploader
                })
                
        except Exception as e:
            print(f"❌ Failed: {e}")
            failed_downloads.append({
                'url': url,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"✅ Successful: {len(successful_downloads)}")
    print(f"❌ Failed: {len(failed_downloads)}")
    
    if successful_downloads:
        print("\n✅ Successfully downloaded:")
        for download in successful_downloads:
            print(f"  - {download['title']} ({download['id']})")
    
    if failed_downloads:
        print("\n❌ Failed downloads:")
        for download in failed_downloads:
            print(f"  - {download['url']}")
            print(f"    Error: {download['error']}")
    
    # List all files in output directory
    print(f"\n📁 Files in {output_dir}:")
    files = list(output_dir.glob("*"))
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Sort by newest first
    
    total_size = 0
    for file in files:
        size_mb = file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  - {file.name} ({size_mb:.1f}MB)")
    
    print(f"\n📊 Total downloaded: {total_size:.1f}MB")
    
    return successful_downloads, failed_downloads

if __name__ == "__main__":
    batch_download_youtube()