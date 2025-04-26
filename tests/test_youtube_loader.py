import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from doc_processing.loaders.youtube_loader import YouTubeLoader

# Mock yt_dlp for testing without actual downloads
class MockYoutubeDL:
    def __init__(self, ydl_opts):
        self.ydl_opts = ydl_opts

    def extract_info(self, url, download=True):
        # Simulate extracting info with and without transcripts
        video_id = "test_video_id"
        info = {
            'id': video_id,
            'title': 'Test Video Title',
            'duration': 120,
            'uploader': 'Test Uploader',
            'webpage_url': url,
            'extractor': 'youtube',
            'extractor_key': 'Youtube',
            'thumbnail': 'http://example.com/thumbnail.jpg',
            'description': 'This is a test video description.',
            'subtitles': None,
            'automatic_captions': None,
        }

        if 'writesubtitles' in self.ydl_opts or 'writeautomaticsub' in self.ydl_opts:
            # Simulate having a transcript
            info['automatic_captions'] = {
                'en': [{'url': 'http://example.com/transcript.vtt', 'ext': 'vtt'}]
            }
            if download:
                # Simulate writing a transcript file
                temp_dir = self.ydl_opts['outtmpl'].rsplit('/', 1)[0]
                transcript_file_path = os.path.join(temp_dir, f"{video_id}.en.vtt")
                with open(transcript_file_path, 'w') as f:
                    f.write("WEBVTT\n\n00:00:00.000 --> 00:00:05.000\nThis is the first part of the transcript.\n\n00:00:05.000 --> 00:00:10.000\nThis is the second part.")
                # Return info without download details for transcript extraction phase
                return info


        if download and 'format' in self.ydl_opts and ('bestaudio' in self.ydl_opts['format'] or 'best' in self.ydl_opts['format']):
             # Simulate downloading audio
             temp_dir = self.ydl_opts['outtmpl'].rsplit('/', 1)[0]
             audio_file_path = os.path.join(temp_dir, f"{video_id}.webm")
             with open(audio_file_path, 'w') as f:
                 f.write("fake audio data")
             # Return info with download details for audio download phase
             info['requested_downloads'] = [{'filepath': audio_file_path}]
             return info


        return info # Default return for info extraction without download

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class TestYouTubeLoader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Patch tempfile.mkdtemp to return our known temp directory
        patcher = patch('doc_processing.loaders.youtube_loader.tempfile.mkdtemp', return_value=self.temp_dir)
        self.mock_mkdtemp = patcher.start()
        self.addCleanup(patcher.stop)

        # Patch yt_dlp.YoutubeDL to use our mock class
        patcher = patch('doc_processing.loaders.youtube_loader.yt_dlp.YoutubeDL', side_effect=MockYoutubeDL)
        self.mock_youtube_dl = patcher.start()
        self.addCleanup(patcher.stop)

        # Remove patching of the audio transcription processor as it's no longer used


    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists(self.temp_dir):
            for root, dirs, files in os.walk(self.temp_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(self.temp_dir)

    def test_load_with_transcript(self):
        """Test loading a YouTube video with an available transcript."""
        loader = YouTubeLoader({})
        youtube_url = "https://www.youtube.com/watch?v=test_video_id"
        # load is no longer async
        result = loader.load(youtube_url)

        self.assertIsNotNone(result)
        self.assertIn("content", result)
        self.assertIn("metadata", result)
        self.assertIsNotNone(result["content"])
        self.assertIn("This is the first part of the transcript.  This is the second part.", result["content"]) # Check extracted transcript
        self.assertEqual(result["metadata"]["source"], youtube_url)
        self.assertEqual(result["metadata"]["title"], "Test Video Title")
        # Add more assertions for metadata as needed

        # Remove assertion related to audio processor


    def test_load_without_transcript_falls_back_to_audio(self):
        """Test loading a YouTube video without a transcript, falling back to audio transcription."""
        # Configure MockYoutubeDL to simulate no transcript
        class MockYoutubeDLNoTranscript(MockYoutubeDL):
            def extract_info(self, url, download=True):
                info = super().extract_info(url, download=download)
                info['subtitles'] = None
                info['automatic_captions'] = None
                return info

        with patch('doc_processing.loaders.youtube_loader.yt_dlp.YoutubeDL', side_effect=MockYoutubeDLNoTranscript):
            loader = YouTubeLoader({})
            youtube_url = "https://www.youtube.com/watch?v=test_video_id_no_transcript"
            # load is no longer async
            result = loader.load(youtube_url)

            self.assertIsNotNone(result)
            self.assertIn("content", result)
            self.assertIn("metadata", result)
            self.assertIsNone(result["content"]) # No transcript content expected
            self.assertIn("video_filepath", result["metadata"]) # Check for video file path in metadata
            video_filepath = result["metadata"]["video_filepath"]
            self.assertTrue(os.path.exists(video_filepath)) # Check if the video file exists

            self.assertEqual(result["metadata"]["source"], youtube_url)
            self.assertEqual(result["metadata"]["title"], "Test Video Title")
            # Add more assertions for metadata as needed

            # Remove assertions related to audio processor

    def test_invalid_url(self):
        """Test loading an invalid URL."""
        loader = YouTubeLoader({})
        invalid_url = "https://notyoutube.com/watch?v=test"
        # Expect ValueError for invalid URL
        with self.assertRaises(ValueError):
            loader.load(invalid_url)

if __name__ == '__main__':
    unittest.main()