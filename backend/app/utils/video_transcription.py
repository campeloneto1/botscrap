"""
Video Transcription utilities using OpenAI Whisper (local).
Transcribes audio from video files to text.
"""
import logging
import tempfile
import os
from typing import Optional, Tuple, List
import httpx
import subprocess

logger = logging.getLogger(__name__)

# Whisper model - use 'base' for balance between speed and quality
# Options: tiny, base, small, medium, large
WHISPER_MODEL = "base"

# Cache for loaded model
_whisper_model = None


def get_whisper_model():
    """Load Whisper model (cached)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info(f"Loading Whisper model: {WHISPER_MODEL}")
            _whisper_model = whisper.load_model(WHISPER_MODEL)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    return _whisper_model


async def download_video(url: str, timeout: int = 60) -> Optional[bytes]:
    """Download video from URL."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'video' in content_type or url.endswith(('.mp4', '.mov', '.webm', '.avi')):
                    return response.content
                logger.warning(f"URL is not a video: {content_type}")
            else:
                logger.warning(f"Failed to download video: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
    return None


def extract_audio_from_video(video_path: str, audio_path: str) -> bool:
    """
    Extract audio from video using ffmpeg.
    Returns True if successful.
    """
    try:
        # Use ffmpeg to extract audio
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',  # Sample rate (Whisper expects 16kHz)
            '-ac', '1',  # Mono
            '-y',  # Overwrite output
            audio_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120  # 2 minutes timeout
        )

        if result.returncode == 0:
            return True
        else:
            logger.warning(f"ffmpeg failed: {result.stderr.decode()}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout")
        return False
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        return False


def transcribe_audio(audio_path: str, language: str = "pt") -> Optional[str]:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file
        language: Language code (default: Portuguese)

    Returns:
        Transcribed text or None if failed
    """
    try:
        model = get_whisper_model()

        logger.info(f"Transcribing audio: {audio_path}")
        result = model.transcribe(
            audio_path,
            language=language,
            fp16=False  # Use FP32 for CPU compatibility
        )

        text = result.get("text", "").strip()

        if text:
            logger.info(f"Transcription successful: {len(text)} characters")
            return text
        else:
            logger.warning("Transcription returned empty text")
            return None

    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None


async def transcribe_video_url(
    video_url: str,
    language: str = "pt"
) -> Tuple[bool, Optional[str]]:
    """
    Download and transcribe video from URL.

    Args:
        video_url: URL of the video
        language: Language for transcription (default: Portuguese)

    Returns:
        Tuple of (success, transcript_text)
    """
    if not video_url:
        return False, None

    logger.info(f"Starting video transcription for: {video_url[:50]}...")

    try:
        # Download video
        video_data = await download_video(video_url)
        if not video_data:
            logger.warning("Failed to download video")
            return False, None

        # Create temp files
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as video_file:
            video_file.write(video_data)
            video_path = video_file.name

        audio_path = video_path.replace('.mp4', '.wav')

        try:
            # Extract audio
            if not extract_audio_from_video(video_path, audio_path):
                logger.warning("Failed to extract audio from video")
                return False, None

            # Transcribe
            transcript = transcribe_audio(audio_path, language)

            if transcript:
                return True, transcript
            else:
                return False, None

        finally:
            # Cleanup temp files
            for path in [video_path, audio_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Error in video transcription: {e}")
        return False, None


async def process_video_for_keywords(
    video_url: str,
    keywords: List[dict],
    language: str = "pt"
) -> Tuple[bool, List[str], int, Optional[str]]:
    """
    Transcribe video and check for keywords.

    Args:
        video_url: URL of the video
        keywords: List of keyword dicts with 'word' and 'priority'
        language: Language for transcription

    Returns:
        Tuple of (has_keyword, matched_keywords, max_priority, transcript)
    """
    success, transcript = await transcribe_video_url(video_url, language)

    if not success or not transcript:
        return False, [], 0, None

    # Check keywords in transcript
    from app.utils.keywords import find_keywords
    has_keyword, matched, priority = find_keywords(transcript, keywords)

    return has_keyword, matched, priority, transcript
