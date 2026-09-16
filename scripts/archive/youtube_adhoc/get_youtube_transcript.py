#!/usr/bin/env python3
"""
Get YouTube transcript directly using yt-dlp
"""

import yt_dlp
from pathlib import Path

def get_transcript(url):
    """Extract transcript from YouTube video"""
    
    # Configuration to just get subtitles
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,  # Don't download video
        'writesubtitles': False,
        'writeautomaticsub': False,
        'subtitleslangs': ['en'],
        'cookiesfrombrowser': ('chrome',),
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Get video metadata
        title = info.get('title', 'Unknown Title')
        uploader = info.get('uploader', 'Unknown')
        duration = info.get('duration', 0)
        video_id = info.get('id', 'Unknown')
        
        print(f"Video: {title}")
        print(f"Uploader: {uploader}")
        print(f"Duration: {duration} seconds")
        print(f"Video ID: {video_id}")
        print("=" * 60)
        
        # Get automatic captions or subtitles
        auto_caps = info.get('automatic_captions', {})
        subtitles = info.get('subtitles', {})
        
        # Prefer manual subtitles over automatic
        en_subs = subtitles.get('en', []) or auto_caps.get('en', [])
        
        if not en_subs:
            print("No English subtitles available!")
            return None
        
        # Find VTT format or any available format
        transcript_url = None
        for sub in en_subs:
            if 'vtt' in sub.get('ext', ''):
                transcript_url = sub.get('url')
                break
        
        # Fallback to first available
        if not transcript_url:
            transcript_url = en_subs[0].get('url')
        
        print(f"Found transcript! Format: {en_subs[0].get('ext', 'unknown')}")
        print(f"Downloading from: {transcript_url[:100]}...")
        
        # Download the transcript content
        import requests
        response = requests.get(transcript_url)
        transcript_raw = response.text
        
        print(f"Downloaded {len(transcript_raw)} characters")
        print(f"First 200 chars: {transcript_raw[:200]}")
        
        # Parse VTT format
        lines = transcript_raw.split('\n')
        transcript_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip WEBVTT header, timestamps, and numbers
            if (line and 
                not line.startswith('WEBVTT') and 
                '-->' not in line and 
                not line.isdigit() and
                not line.startswith('<') and
                not line.startswith('align:')):
                # Clean up the text
                import re
                clean_line = re.sub(r'<[^>]+>', '', line)  # Remove HTML tags
                clean_line = re.sub(r'&nbsp;', ' ', clean_line)  # Replace nbsp
                clean_line = clean_line.strip()
                if clean_line:
                    transcript_lines.append(clean_line)
        
        # Join the transcript
        full_transcript = ' '.join(transcript_lines)
        
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
        
        # Save to file
        output_dir = Path('data/output/youtube/transcripts')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{video_id}_transcript.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        
        print(f"\n✅ Transcript saved to: {output_file}")
        print(f"\nTranscript Preview:")
        print("-" * 40)
        print(full_transcript[:1000] + "..." if len(full_transcript) > 1000 else full_transcript)
        
        return output_file

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=zWfX5jeF6k4"
    get_transcript(url)