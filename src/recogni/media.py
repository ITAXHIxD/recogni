"""Local media validation and metadata extraction using FFprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {
    ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpeg", ".mpg"
}


class MediaValidationError(ValueError):
    """Raised when a selected file is not a readable supported video."""


@dataclass(frozen=True)
class MediaMetadata:
    path: Path
    duration_seconds: float
    width: int
    height: int
    frame_rate: float | None
    has_audio: bool
    format_name: str


def _parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", maxsplit=1)
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        return float(numerator) / denominator_value
    except (ValueError, ZeroDivisionError):
        return None


def probe_video(path: str | Path, *, timeout_seconds: int = 20) -> MediaMetadata:
    """Validate a local video and return metadata, without modifying the source.

    FFprobe is invoked with an argument list (never through a shell) so paths
    containing spaces or shell metacharacters are handled safely.
    """
    video_path = Path(path).expanduser()

    if not video_path.exists() or not video_path.is_file():
        raise MediaValidationError("The selected file does not exist or is not a file.")
    if video_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise MediaValidationError(
            f"Unsupported video extension '{video_path.suffix or '(none)'}'. "
            f"Supported extensions: {allowed}."
        )

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise MediaValidationError(
            "FFprobe was not found. Install FFmpeg and add its bin folder to PATH, "
            "then restart RECOGNI."
        )

    command = [
        ffprobe,
        "-v", "error",
        "-show_entries",
        "format=duration,format_name:stream=codec_type,width,height,avg_frame_rate",
        "-of", "json",
        str(video_path.resolve()),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaValidationError("Video inspection timed out.") from exc
    except OSError as exc:
        raise MediaValidationError(f"Could not start FFprobe: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or "The media file could not be decoded."
        raise MediaValidationError(f"Invalid or unreadable video: {detail}")

    try:
        payload: dict[str, Any] = json.loads(result.stdout)
        media_format = payload.get("format") or {}
        streams = payload.get("streams") or []
        video_stream = next(
            (stream for stream in streams if stream.get("codec_type") == "video"),
            None,
        )
        if not video_stream:
            raise MediaValidationError("The selected file contains no video stream.")

        duration = float(media_format.get("duration", 0))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        if duration <= 0 or width <= 0 or height <= 0:
            raise MediaValidationError(
                "The video metadata is incomplete or the video has no usable duration."
            )

        return MediaMetadata(
            path=video_path.resolve(),
            duration_seconds=duration,
            width=width,
            height=height,
            frame_rate=_parse_rate(video_stream.get("avg_frame_rate")),
            has_audio=any(s.get("codec_type") == "audio" for s in streams),
            format_name=str(media_format.get("format_name", "unknown")),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, MediaValidationError):
            raise
        raise MediaValidationError("FFprobe returned invalid media metadata.") from exc
