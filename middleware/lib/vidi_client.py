"""Vidi 7B Video Understanding Client.

Provides interface to Vidi 7B model for video analysis tasks:
- Video Q&A (VQA)
- Temporal grounding (timestamp finding)
- Video clip extraction
"""

import os
import re
import subprocess
import logging
import requests
from typing import List, Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VidiClient:
    """Client for Vidi 7B video understanding model.

    Vidi runs on HOST (not in container) at http://host.docker.internal:8099
    similar to ComfyUI architecture.
    """

    def __init__(self, base_url: str = "http://host.docker.internal:8099"):
        """Initialize Vidi client.

        Args:
            base_url: Base URL for Vidi server (default: host.docker.internal:8099)
        """
        self.base_url = base_url.rstrip('/')
        self._available = None
        logger.info(f"Initialized VidiClient with base_url: {self.base_url}")

    def is_available(self) -> bool:
        """Check if Vidi server is available.

        Returns:
            bool: True if server is reachable and responding
        """
        if self._available is not None:
            return self._available

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self._available = response.status_code == 200
            logger.info(f"Vidi availability check: {self._available}")
            return self._available
        except Exception as e:
            logger.warning(f"Vidi not available: {e}")
            self._available = False
            return False

    def ask_vqa(self, video_path: str, question: str, timeout: int = 120) -> str:
        """Ask a question about a video (Video Question Answering).

        Args:
            video_path: Path to video file
            question: Question to ask about the video
            timeout: Request timeout in seconds (default: 120)

        Returns:
            str: Answer from Vidi model

        Raises:
            RuntimeError: If Vidi is not available
            requests.RequestException: If request fails
        """
        if not self.is_available():
            raise RuntimeError("Vidi server is not available")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Asking Vidi VQA: {question[:100]}...")

        try:
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'question': question,
                    'task': 'vqa'  # Generic VQA task
                }

                response = requests.post(
                    f"{self.base_url}/inference",
                    files=files,
                    data=data,
                    timeout=timeout
                )
                response.raise_for_status()

                result = response.json()
                answer = result.get('answer', '')
                logger.info(f"Vidi VQA response: {answer[:200]}...")
                return answer

        except requests.RequestException as e:
            logger.error(f"Vidi VQA request failed: {e}")
            raise

    def find_timestamps(self, video_path: str, query: str, timeout: int = 180) -> List[Tuple[float, float]]:
        """Find temporal locations matching a text query (retrieval task).

        Args:
            video_path: Path to video file
            query: Text query describing what to find
            timeout: Request timeout in seconds (default: 180)

        Returns:
            List of (start_time, end_time) tuples in seconds

        Raises:
            RuntimeError: If Vidi is not available
            requests.RequestException: If request fails
        """
        if not self.is_available():
            raise RuntimeError("Vidi server is not available")

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Finding timestamps for: {query[:100]}...")

        try:
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'question': query,
                    'task': 'retrieval'  # Temporal grounding task
                }

                response = requests.post(
                    f"{self.base_url}/inference",
                    files=files,
                    data=data,
                    timeout=timeout
                )
                response.raise_for_status()

                result = response.json()
                timestamps_str = result.get('answer', '')

                # Parse timestamps from format: "00:00:10.00-00:00:15.50, 00:00:30.00-00:00:35.00"
                timestamps = self._parse_timestamps(timestamps_str)
                logger.info(f"Found {len(timestamps)} timestamp ranges")
                return timestamps

        except requests.RequestException as e:
            logger.error(f"Vidi timestamp request failed: {e}")
            raise

    def extract_clips(self, video_path: str, timestamps: List[Tuple[float, float]],
                     output_dir: str) -> List[str]:
        """Extract video clips from timestamp ranges.

        Args:
            video_path: Path to source video
            timestamps: List of (start_time, end_time) tuples in seconds
            output_dir: Directory to save extracted clips

        Returns:
            List of paths to extracted clip files

        Raises:
            RuntimeError: If ffmpeg is not available
        """
        os.makedirs(output_dir, exist_ok=True)
        clip_paths = []

        video_name = Path(video_path).stem

        for i, (start, end) in enumerate(timestamps):
            output_path = os.path.join(output_dir, f"{video_name}_clip_{i+1}.mp4")

            try:
                # Use ffmpeg to extract clip
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-ss', str(start),
                    '-to', str(end),
                    '-c', 'copy',  # Copy codec (fast, no re-encoding)
                    '-y',  # Overwrite output
                    output_path
                ]

                logger.info(f"Extracting clip {i+1}: {start:.2f}s - {end:.2f}s")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    clip_paths.append(output_path)
                    logger.info(f"Clip saved: {output_path}")
                else:
                    logger.error(f"ffmpeg failed: {result.stderr}")

            except subprocess.TimeoutExpired:
                logger.error(f"ffmpeg timeout for clip {i+1}")
            except Exception as e:
                logger.error(f"Failed to extract clip {i+1}: {e}")

        return clip_paths

    def _parse_timestamps(self, timestamps_str: str) -> List[Tuple[float, float]]:
        """Parse timestamp string to list of (start, end) tuples.

        Expects format: "HH:MM:SS.ss-HH:MM:SS.ss, HH:MM:SS.ss-HH:MM:SS.ss"

        Args:
            timestamps_str: String containing timestamp ranges

        Returns:
            List of (start_seconds, end_seconds) tuples
        """
        timestamps = []

        # Pattern: HH:MM:SS or HH:MM:SS.ss
        time_pattern = r'(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)'
        range_pattern = f'{time_pattern}-{time_pattern}'

        matches = re.finditer(range_pattern, timestamps_str)

        for match in matches:
            # Start time
            start_h, start_m, start_s = match.groups()[:3]
            start_seconds = int(start_h) * 3600 + int(start_m) * 60 + float(start_s)

            # End time
            end_h, end_m, end_s = match.groups()[3:]
            end_seconds = int(end_h) * 3600 + int(end_m) * 60 + float(end_s)

            timestamps.append((start_seconds, end_seconds))

        return timestamps
