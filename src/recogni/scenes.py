"""Local FFmpeg visual scene-cut detection."""
from __future__ import annotations
import re, shutil, subprocess
from dataclasses import dataclass
from pathlib import Path

_TIMESTAMP_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")

class SceneDetectionError(RuntimeError):
    """FFmpeg scene detection failed."""

@dataclass(frozen=True)
class Scene:
    start_seconds: float
    end_seconds: float
    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)

def parse_scene_timestamps(stderr: str, duration_seconds: float) -> list[float]:
    """Parse unique, in-range timestamps emitted by FFmpeg's showinfo filter."""
    if duration_seconds <= 0:
        return []
    return sorted({float(m.group(1)) for m in _TIMESTAMP_RE.finditer(stderr)
                   if 0 < float(m.group(1)) < duration_seconds})

def build_scenes(cut_timestamps: list[float], duration_seconds: float) -> list[Scene]:
    """Create contiguous intervals spanning the complete video."""
    if duration_seconds <= 0:
        return []
    cuts = sorted({float(v) for v in cut_timestamps if 0 < float(v) < duration_seconds})
    boundaries = [0.0, *cuts, float(duration_seconds)]
    return [Scene(a, b) for a, b in zip(boundaries, boundaries[1:]) if b > a]

def detect_scenes(path: str | Path, duration_seconds: float, *,
                  threshold: float = 0.35, timeout_seconds: int = 1800) -> list[Scene]:
    """Detect visual cuts locally. A lower threshold finds subtler transitions."""
    video = Path(path).expanduser()
    if not video.is_file():
        raise SceneDetectionError("The selected video file no longer exists.")
    if not 0 < threshold < 1:
        raise ValueError("threshold must be between 0 and 1.")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SceneDetectionError("FFmpeg was not found. Install FFmpeg, add its bin folder to PATH, and restart RECOGNI.")
    command = [ffmpeg, "-hide_banner", "-nostats", "-i", str(video.resolve()),
               "-vf", f"select='gt(scene,{threshold})',showinfo",
               "-an", "-sn", "-dn", "-f", "null", "-"]
    try:
        result = subprocess.run(command, capture_output=True, text=True,
                                timeout=timeout_seconds, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise SceneDetectionError("Scene detection timed out. Try a shorter video.") from exc
    except OSError as exc:
        raise SceneDetectionError(f"Could not start FFmpeg: {exc}") from exc
    if result.returncode != 0:
        lines = result.stderr.strip().splitlines()
        detail = lines[-1] if lines else "FFmpeg could not decode this video."
        raise SceneDetectionError(f"FFmpeg scene detection failed: {detail}")
    scenes = build_scenes(parse_scene_timestamps(result.stderr, duration_seconds), duration_seconds)
    if not scenes:
        raise SceneDetectionError("No usable scene intervals could be created.")
    return scenes
