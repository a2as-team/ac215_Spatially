import sys
import unittest
from pathlib import Path

# Add parent directory to path to import collector modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from collector.zba.boston import BostonZBACollector


class TestBostonZBATranscription(unittest.TestCase):
    """Test cases for Boston ZBA video transcription."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.collector = BostonZBACollector()
        cls.test_output_dir = "tmp/test_transcripts"

    def test_transcribe_single_video(self):
        """Test transcription with a single video."""
        # Get video data
        video_data = self.collector.collect_video_urls()
        self.assertGreater(len(video_data), 0, "Should have video data")

        # Get just the first video for testing
        first_date = list(video_data.keys())[0]
        first_url = video_data[first_date]

        # If it's a list, take just the first video
        if isinstance(first_url, list):
            first_url = first_url[0]

        test_data = {first_date: first_url}

        print(f"\nTesting transcription for: {first_date}")
        print(f"URL: {first_url}")

        # Transcribe
        self.collector._transcribe_video_urls(
            test_data, output_dir=self.test_output_dir
        )

        # Check that transcript was created
        output_path = Path(self.test_output_dir) / "zba" / "boston"
        date_formatted = first_date.replace(", ", "_").replace(" ", "_")
        transcript_file = output_path / f"{date_formatted}.txt"
        segments_file = output_path / f"{date_formatted}_segments.json"

        self.assertTrue(
            transcript_file.exists(),
            f"Transcript should exist at {transcript_file}",
        )
        self.assertTrue(
            segments_file.exists(),
            f"Segments file should exist at {segments_file}",
        )

        # Check that transcript has content
        with open(transcript_file, "r") as f:
            content = f.read()
        self.assertGreater(len(content), 0, "Transcript should have content")

        # Check that segments file has valid JSON
        import json
        with open(segments_file, "r") as f:
            segments_data = json.load(f)
        self.assertIn("metadata", segments_data, "Segments should have metadata")
        self.assertIn("text", segments_data, "Segments should have text")
        self.assertIn("segments", segments_data, "Segments should have segments list")

        print(f"\n✓ Transcript created: {transcript_file}")
        print(f"  Length: {len(content)} characters")
        print(f"✓ Segments file created: {segments_file}")
        print(f"  Number of segments: {len(segments_data['segments'])}")


if __name__ == "__main__":
    unittest.main()
