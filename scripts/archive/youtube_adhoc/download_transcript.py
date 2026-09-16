#!/usr/bin/env python3
"""
Download YouTube transcript using yt-dlp with subtitle files
"""

import yt_dlp
import json
from pathlib import Path

def download_with_transcript(url):
    """Download YouTube video transcript"""
    
    output_dir = Path('data/output/youtube')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configuration to download subtitles
    ydl_opts = {
        'outtmpl': str(output_dir / 'temp_%(id)s.%(ext)s'),
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'skip_download': True,  # Skip video download, only get subtitles
        'quiet': False,
        'cookiesfrombrowser': ('chrome',),
    }
    
    print("Downloading transcript from YouTube...")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        # Get video metadata
        title = info.get('title', 'Unknown Title')
        uploader = info.get('uploader', 'Unknown')
        duration = info.get('duration', 0)
        video_id = info.get('id', 'Unknown')
        
        print(f"\nVideo: {title}")
        print(f"Uploader: {uploader}")
        print(f"Duration: {duration} seconds")
        print(f"Video ID: {video_id}")
        
        # Check for downloaded subtitle file
        subtitle_file = output_dir / f"temp_{video_id}.en.vtt"
        
        if subtitle_file.exists():
            print(f"\n✅ Found subtitle file: {subtitle_file}")
            
            # Read and parse the VTT file
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                vtt_content = f.read()
            
            # Parse VTT to extract text
            lines = vtt_content.split('\n')
            transcript_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip WEBVTT header, timestamps, and empty lines
                if (line and 
                    not line.startswith('WEBVTT') and 
                    not line.startswith('Kind:') and
                    not line.startswith('Language:') and
                    '-->' not in line and 
                    not line.isdigit()):
                    # Clean HTML tags
                    import re
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    clean_line = re.sub(r'&nbsp;', ' ', clean_line)
                    clean_line = clean_line.strip()
                    if clean_line:
                        transcript_lines.append(clean_line)
            
            full_transcript = ' '.join(transcript_lines)
            
            # Remove duplicate consecutive words (common in auto-captions)
            words = full_transcript.split()
            cleaned_words = [words[0]] if words else []
            for word in words[1:]:
                if word != cleaned_words[-1]:
                    cleaned_words.append(word)
            full_transcript = ' '.join(cleaned_words)
            
            # Create markdown output
            markdown_output = f"""# {title}

**Video ID:** {video_id}  
**Uploader:** {uploader}  
**Duration:** {duration} seconds  
**URL:** {url}

---

## Transcript

{full_transcript}

---

*Transcript extracted from YouTube automatic captions/subtitles*
"""
            
            # Save to markdown file
            transcript_dir = output_dir / 'transcripts'
            transcript_dir.mkdir(exist_ok=True)
            
            output_file = transcript_dir / f"{video_id}_transcript.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_output)
            
            # Clean up temporary subtitle file
            subtitle_file.unlink()
            
            print(f"\n✅ Transcript saved to: {output_file}")
            print(f"\nTranscript Preview:")
            print("-" * 40)
            print(full_transcript[:1000] + "..." if len(full_transcript) > 1000 else full_transcript)
            
            return output_file
        else:
            print(f"\n❌ No subtitle file found at {subtitle_file}")
            print("The video might not have subtitles available.")
            return None

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=zWfX5jeF6k4"
    download_with_transcript(url)