from abc import ABC, abstractmethod
import json
import time
from typing import Dict, List, Union
from pathlib import Path

import requests


class BaseZBACollector(ABC):
    city = ""
    zba_url = ""

    def __init__(self, city: str, zba_url: str):
        self.city = city
        self.zba_url = zba_url
        if not self.city:
            raise ValueError("City is required")
        if not self.zba_url:
            raise ValueError("ZBA URL is required")

    @abstractmethod
    def collect_video_urls(self) -> Dict[str, Union[str, List[str]]]:
        """
        This should go into the zba url and find the video urls since
        the zbas are best informed by the video recordings.
        We should use bs4 or selenium to find the video urls.

        Returns:
            Dict mapping dates to video URLs (single URL or list of
            URLs for multiple parts)
        """
        pass

    def _transcribe_video_urls(
        self,
        video_data: Dict[str, Union[str, List[str]]],
        output_dir: str = "tmp/transcripts",
        model_size: str = "small",
        language: str = "en",
    ):
        """
        Transcribe videos using Whisper and save transcripts by date.
        If CUDA is unavailable, only transcribes the first video as a test.

        Args:
            video_data: Dict mapping dates to video URLs
            output_dir: Directory to save transcripts
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            language: Language code for transcription (e.g., 'en' for English).
                     Set to None for auto-detection.
        """
        try:
            import whisper
            from yt_dlp import YoutubeDL
        except ImportError as e:
            msg = (
                "Required packages not installed. "
                "Install with: uv add openai-whisper yt-dlp"
            )
            raise ImportError(msg) from e

        # Check CUDA availability
        import torch

        cuda_available = torch.cuda.is_available()

        if not cuda_available:
            print("⚠️  CUDA not available - running in CPU mode")
            print("⚠️  Will only transcribe the FIRST video for testing")
            # Limit to first video only
            first_date = list(video_data.keys())[0]
            video_data = {first_date: video_data[first_date]}

        output_path = Path(output_dir) / "zba" / self.city.lower()
        output_path.mkdir(parents=True, exist_ok=True)

        device = "cuda" if cuda_available else "cpu"
        print(f"Loading Whisper '{model_size}' model on {device}...")
        model = whisper.load_model(model_size, device=device)

        for date, urls in video_data.items():
            # Handle both single URL and list of URLs
            url_list = [urls] if isinstance(urls, str) else urls

            for idx, url in enumerate(url_list):
                # Create filename from date and part number
                if len(url_list) > 1:
                    part_suffix = f"_part{idx + 1}"
                else:
                    part_suffix = ""

                date_formatted = date.replace(", ", "_").replace(" ", "_")
                filename = f"{date_formatted}{part_suffix}"
                transcript_file = output_path / f"{filename}.txt"

                if transcript_file.exists():
                    print(f"Transcript already exists: {transcript_file}")
                    continue

                try:
                    print(f"Downloading audio from: {url}")
                    # Download audio from YouTube and extract metadata
                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": str(output_path / f"{filename}.%(ext)s"),
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "wav",
                                "preferredquality": "0",  # Best quality
                            }
                        ],
                    }

                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        video_metadata = {
                            "title": info.get("title", ""),
                            "duration": info.get("duration", 0),
                            "upload_date": info.get("upload_date", ""),
                            "url": url,
                            "date": date,
                        }

                    audio_file = output_path / f"{filename}.wav"

                    print(f"Transcribing: {audio_file}")
                    # Use fp16 for GPU acceleration and provide context
                    transcribe_options = {
                        "verbose": False,  # Disable verbose segment output
                        "initial_prompt": "This is a zoning board of appeal meeting with discussions about variances, building permits, and city planning.",
                    }
                    if language:
                        transcribe_options["language"] = language
                    if cuda_available:
                        transcribe_options["fp16"] = True

                    result = model.transcribe(str(audio_file), **transcribe_options)
                    print(f"✓ Transcription complete")

                    # Save plain text transcript
                    with open(transcript_file, "w") as f:
                        f.write(result["text"])

                    print(f"Saved transcript: {transcript_file}")

                    # Save detailed segments with timestamps and metadata
                    segments_file = output_path / f"{filename}_segments.json"
                    segments_data = {
                        "metadata": video_metadata,
                        "text": result["text"],
                        "language": result.get("language", language),
                        "segments": [
                            {
                                "id": seg["id"],
                                "start": seg["start"],
                                "end": seg["end"],
                                "text": seg["text"],
                            }
                            for seg in result.get("segments", [])
                        ],
                    }
                    with open(segments_file, "w") as f:
                        json.dump(segments_data, f, indent=2)

                    print(f"Saved segments: {segments_file}")

                    # Clean up audio file
                    audio_file.unlink()

                except Exception as e:
                    print(f"Error transcribing {url}: {e}")
                    continue

    def collect(self):
        video_data = self.collect_video_urls()
        print(f"Found {len(video_data)} dates with videos")
        self._transcribe_video_urls(video_data)
