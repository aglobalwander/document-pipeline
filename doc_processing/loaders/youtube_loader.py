import os
import tempfile
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from doc_processing.embedding.base import BaseDocumentLoader
from .video_loader import VideoLoader

import yt_dlp

class YouTubeLoader(BaseDocumentLoader):
    """
    A loader for processing YouTube video URLs.

    This loader downloads the video content using yt-dlp and then
    uses the VideoLoader to process the downloaded file.
    """
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.video_loader = VideoLoader(config.get('video_loader_config', {})) # Pass relevant config to VideoLoader

    def load(self, source: Union[str, Path]) -> Dict[str, Any]:
        """
        Loads content from a YouTube URL by extracting metadata and transcript,
        falling back to audio transcription if no transcript is available.

        Args:
            source: The YouTube video URL.

        Returns:
            A dictionary containing the transcript content and metadata.
        """
        input_path = str(source)
        if not self._is_youtube_url(input_path):
            raise ValueError(f"Invalid YouTube URL: {input_path}")
        temp_dir = None
        transcript_content = None

        try:
            # Use yt-dlp to extract info including transcripts
            ydl_opts_info = {
                'extract_flat': 'discard_key',
                'noplaylist': True,
                'quiet': True,
                'progress': False,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'], # Prioritize English transcripts
                'skip_download': True, # Don't download video/audio yet
            }
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info_dict = ydl.extract_info(input_path, download=False)

            video_id = info_dict.get('id')
            if not video_id:
                 raise ValueError(f"Could not extract video ID from {input_path}")

            # Check for available transcripts (subtitles or automatic captions)
            transcripts = info_dict.get('subtitles') or info_dict.get('automatic_captions')

            if transcripts:
                self.logger.info(f"Transcript found for {input_path}. Extracting...")
                # yt-dlp writes transcripts to files when writesubtitles/writeautomaticsub is True
                # We need to find the downloaded transcript file
                temp_dir = tempfile.mkdtemp()
                ydl_opts_transcript = {
                    'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                    'noplaylist': True,
                    'quiet': True,
                    'progress': False,
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en'],
                    'skip_download': True, # Still skip video/audio download
                }
                with yt_dlp.YoutubeDL(ydl_opts_transcript) as ydl:
                     ydl.extract_info(input_path, download=True) # Download only the transcript

                # Find the downloaded transcript file (e.g., video_id.en.vtt or video_id.en.srv1)
                transcript_file = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.startswith(video_id) and ('.vtt' in file or '.srv' in file or '.ttml' in file):
                            transcript_file = os.path.join(root, file)
                            break
                    if transcript_file:
                        break

                if transcript_file and os.path.exists(transcript_file):
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        # Basic VTT/SRV/TTML parsing to get raw text
                        # This is a simplified approach; a more robust parser might be needed
                        lines = f.readlines()
                        transcript_content = ""
                        for line in lines:
                            # Skip lines that look like timestamps, cue identifiers, or metadata
                            if '-->' not in line and not line.strip().isdigit() and not line.startswith('WEBVTT') and not line.startswith('<?xml'):
                                transcript_content += line.strip() + " "
                        transcript_content = transcript_content.strip()
                    self.logger.info(f"Successfully extracted transcript for {input_path}")
                else:
                    self.logger.warning(f"Transcript file not found after download attempt for {input_path}")
                    # Fallback to audio download if transcript file extraction failed
                    transcripts = None # Force fallback to audio

            if not transcripts:
                self.logger.info(f"No transcript found or extracted for {input_path}. Downloading video for post-processing...")
                temp_dir = tempfile.mkdtemp() # Create temp dir if not already created
                # Download the best video format
                ydl_opts_video = {
                    'format': 'bestvideo+bestaudio/best', # Download best video and audio and merge
                    'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
                    'noplaylist': True,
                    'quiet': True,
                    'progress': False,
                }
                with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
                    info_dict_video = ydl.extract_info(input_path, download=True)
                    video_file = None
                    # Find the downloaded video file
                    # yt-dlp might save as .webm or .mp4 depending on the best format
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            # Check for files that match the video id and common video extensions
                            if info_dict_video['id'] in file and (file.endswith('.webm') or file.endswith('.mp4')):
                                video_file = os.path.join(root, file)
                                break
                        if video_file:
                            break

                    if video_file and os.path.exists(video_file):
                        self.logger.info(f"Video downloaded to {video_file} for post-processing.")
                        # Set transcript_content to None as no transcript was found
                        transcript_content = None
                        # Add the video file path to the metadata
                        info_dict['video_filepath'] = video_file
                    else:
                         raise FileNotFoundError(f"Could not find downloaded video file for {input_path}")


            # Extract relevant metadata (using info_dict which contains info from initial extraction or video download)
            metadata = {
                "source": input_path,
                "source_type": "youtube",
                "title": info_dict.get('title', 'YouTube Video'),
                "duration_sec": info_dict.get('duration'),
                "uploader": info_dict.get('uploader'),
                "upload_date": info_dict.get('upload_date'), # YYYYMMDD format
                "categories": info_dict.get('categories'),
                "tags": info_dict.get('tags'),
                "view_count": info_dict.get('view_count'),
                "like_count": info_dict.get('like_count'),
                "channel_id": info_dict.get('channel_id'),
                "channel_url": info_dict.get('channel_url'),
                "webpage_url": info_dict.get('webpage_url'),
                "extractor": info_dict.get('extractor'),
                "extractor_key": info_dict.get('extractor_key'),
                "id": info_dict.get('id'),
                "thumbnail": info_dict.get('thumbnail'),
                "description": info_dict.get('description'),
                "video_filepath": info_dict.get('video_filepath'), # Include video file path if downloaded
                # Add other relevant metadata fields as needed
            }

            return {
                "content": transcript_content,
                "metadata": metadata
            }

        finally:
            # Clean up the temporary directory and its contents
            if temp_dir and os.path.exists(temp_dir):
                try:
                    # Keep the video file if it was downloaded and no transcript was found
                    if 'video_filepath' in metadata and metadata['video_filepath'] and os.path.exists(metadata['video_filepath']):
                         self.logger.info(f"Keeping downloaded video file: {metadata['video_filepath']}")
                         # Remove all other files in the temp directory except the video file
                         for root, dirs, files in os.walk(temp_dir, topdown=False):
                             for name in files:
                                 file_path = os.path.join(root, name)
                                 if file_path != metadata['video_filepath']:
                                     os.remove(file_path)
                             # Remove empty directories
                             for name in dirs:
                                 dir_path = os.path.join(root, name)
                                 if not os.listdir(dir_path): # Check if directory is empty
                                     os.rmdir(dir_path)
                         # Do not remove the temp_dir itself if it still contains the video file
                         if not os.listdir(temp_dir): # Check if temp_dir is empty after cleanup
                             os.rmdir(temp_dir)
                             self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                         else:
                             self.logger.info(f"Temporary directory {temp_dir} not removed as it contains the downloaded video file.")

                    else:
                        # If no video file was kept, clean up the entire temp directory
                        for root, dirs, files in os.walk(temp_dir, topdown=False):
                            for name in files:
                                os.remove(os.path.join(root, name))
                            for name in dirs:
                                os.rmdir(os.path.join(root, name))
                        os.rmdir(temp_dir)
                        self.logger.info(f"Cleaned up temporary directory: {temp_dir}")

                except Exception as cleanup_error:
                    self.logger.error(f"Error during temporary directory cleanup {temp_dir}: {cleanup_error}")


    def _is_youtube_url(self, input_path: str) -> bool:
        """
        Checks if the input_path is a valid YouTube URL.
        """
        if not isinstance(input_path, str):
            print(f"_is_youtube_url: Input is not a string: {input_path}. Returning False.") # Added print
            return False
        # Basic check for common YouTube URL patterns
        # Check if the URL starts with a valid YouTube domain
        valid_domains = ['https://www.youtube.com/', 'http://www.youtube.com/', 'https://youtu.be/', 'http://youtu.be/']
        is_youtube = any(input_path.startswith(domain) for domain in valid_domains)
        print(f"_is_youtube_url: Input: {input_path}, Result: {is_youtube}") # Added print
        return is_youtube