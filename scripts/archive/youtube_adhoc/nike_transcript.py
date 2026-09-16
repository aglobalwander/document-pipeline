#!/usr/bin/env python3
"""
Get Nike Dream Crazier transcript using youtube-transcript-api
"""

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from pathlib import Path

def get_nike_transcript():
    video_id = '5sMBhDv4sik'
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Get the transcript  
        api = YouTubeTranscriptApi()
        transcript_list = api.fetch(video_id, ['en'])
        
        # Extract just the text
        transcript_text = ' '.join([entry['text'] for entry in transcript_list])
        
        # Create markdown output
        markdown_output = f"""# Nike - Dream Crazier | #JustDoIt

**Video ID:** {video_id}  
**URL:** {url}

---

## Transcript

{transcript_text}

---

*Transcript extracted from YouTube automatic captions*
"""
        
        # Save to file
        output_dir = Path('data/output/youtube/transcripts')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{video_id}_transcript.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_output)
        
        print(f"✅ Transcript saved to: {output_file}")
        print(f"\nTranscript:")
        print("-" * 60)
        print(transcript_text)
        
        return output_file
        
    except Exception as e:
        print(f"Error getting transcript: {e}")
        print("\nTrying to get available transcripts...")
        
        try:
            # List available transcripts
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)
            
            print("Available transcripts:")
            for transcript in transcript_list:
                print(f"  - Language: {transcript.language}, Code: {transcript.language_code}")
                print(f"    Is generated: {transcript.is_generated}")
                print(f"    Is translatable: {transcript.is_translatable}")
                
        except Exception as e2:
            print(f"Error listing transcripts: {e2}")

if __name__ == "__main__":
    get_nike_transcript()