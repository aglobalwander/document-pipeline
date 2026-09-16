#!/usr/bin/env python3
"""
Extract and format YouTube transcript from downloaded metadata
"""

import json
import requests
import re
from pathlib import Path

def process_embedded_transcript(content, title, video_id, uploader, duration):
    """Process embedded transcript content"""
    # Clean up the content
    lines = content.split('\n')
    transcript_text = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('WEBVTT') and '-->' not in line and not line.strip().isdigit():
            # Remove timestamps and tags
            clean_line = re.sub(r'<[^>]+>', '', line)  # Remove HTML tags
            clean_line = re.sub(r'\[.*?\]', '', clean_line)  # Remove brackets
            if clean_line.strip():
                transcript_text.append(clean_line.strip())
    
    formatted_transcript = ' '.join(transcript_text)
    
    # Create markdown output
    markdown_output = f"""# {title}

**Video ID:** {video_id}  
**Uploader:** {uploader}  
**Duration:** {duration} seconds  
**URL:** https://www.youtube.com/watch?v={video_id}

---

## Transcript

{formatted_transcript}

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
    print(f"\nTranscript Preview (first 500 chars):")
    print("-" * 40)
    print(formatted_transcript[:500] if formatted_transcript else "No transcript content found")
    
    return output_file

def extract_transcript(json_file_path):
    """Extract transcript from YouTube metadata JSON file"""
    
    # Read the JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get video title and info
    title = data.get('title', 'Unknown Title')
    uploader = data.get('uploader', 'Unknown')
    duration = data.get('duration', 0)
    video_id = data.get('id', 'Unknown')
    
    print(f"Extracting transcript for: {title}")
    print(f"Uploader: {uploader}")
    print(f"Duration: {duration} seconds")
    print(f"Video ID: {video_id}")
    print("=" * 60)
    
    # Try to get subtitles or automatic captions
    subtitles = data.get('subtitles', {})
    auto_captions = data.get('automatic_captions', {})
    
    # Prefer manual subtitles over automatic captions
    en_subs = subtitles.get('en', []) or auto_captions.get('en', [])
    
    if not en_subs:
        print("No English subtitles found!")
        # Check if requested_subtitles has the actual content
        requested_subs = data.get('requested_subtitles', {})
        if requested_subs and 'en' in requested_subs:
            sub_data = requested_subs['en']
            if sub_data and '_content' in sub_data:
                print("Found embedded subtitle content!")
                transcript_content = sub_data['_content']
                # Process embedded content directly
                return process_embedded_transcript(transcript_content, title, video_id, uploader, duration)
        return None
    
    # Find the best format (prefer vtt or srv3)
    transcript_url = None
    for sub in en_subs:
        if 'vtt' in sub.get('ext', ''):
            transcript_url = sub.get('url')
            break
        elif 'srv3' in sub.get('ext', ''):
            transcript_url = sub.get('url')
            break
        elif 'json3' in sub.get('ext', ''):
            transcript_url = sub.get('url')
            break
    
    # Fallback to first available
    if not transcript_url and en_subs:
        transcript_url = en_subs[0].get('url')
    
    if not transcript_url:
        print("No transcript URL found!")
        return None
    
    print(f"Downloading transcript from YouTube...")
    
    # Download the transcript
    try:
        response = requests.get(transcript_url, timeout=30)
        response.raise_for_status()
        transcript_content = response.text
    except Exception as e:
        print(f"Error downloading transcript: {e}")
        return None
    
    # Process the transcript based on format
    formatted_transcript = ""
    
    if 'json3' in transcript_url:
        # Parse JSON3 format
        try:
            json_data = json.loads(transcript_content)
            events = json_data.get('events', [])
            transcript_text = []
            
            for event in events:
                if 'segs' in event:
                    for seg in event['segs']:
                        text = seg.get('utf8', '').strip()
                        if text and text != '\n':
                            transcript_text.append(text)
            
            formatted_transcript = ''.join(transcript_text)
        except json.JSONDecodeError:
            print("Failed to parse JSON3 format")
            
    elif 'vtt' in transcript_url or 'WEBVTT' in transcript_content[:20]:
        # Parse VTT format
        lines = transcript_content.split('\n')
        transcript_text = []
        
        for i, line in enumerate(lines):
            # Skip WEBVTT header, timestamps, and empty lines
            if line.strip() and not line.startswith('WEBVTT') and '-->' not in line and not line.strip().isdigit():
                # Clean up the line (remove tags if any)
                clean_line = re.sub(r'<[^>]+>', '', line.strip())  # Remove HTML tags
                if clean_line and clean_line not in transcript_text:  # Avoid duplicates
                    transcript_text.append(clean_line)
        
        formatted_transcript = ' '.join(transcript_text)
    else:
        # For other formats, try to extract text content
        formatted_transcript = transcript_content
    
    # Clean up the transcript
    formatted_transcript = re.sub(r'\s+', ' ', formatted_transcript).strip()
    
    # Create markdown output
    markdown_output = f"""# {title}

**Video ID:** {video_id}  
**Uploader:** {uploader}  
**Duration:** {duration} seconds  
**URL:** https://www.youtube.com/watch?v={video_id}

---

## Transcript

{formatted_transcript}

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
    print(f"\nTranscript Preview (first 500 chars):")
    print("-" * 40)
    print(formatted_transcript[:500])
    
    return output_file

if __name__ == "__main__":
    # Process the Apple Think Different video
    json_file = "data/output/youtube/Apple - Think Different - Full Version_5sMBhDv4sik.info.json"
    extract_transcript(json_file)