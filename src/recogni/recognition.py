"""Local sampled-frame face analysis using OpenCV YuNet and SFace.

Face clusters are candidates for human review, not guaranteed identities.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import cv2
import numpy as np

_MODEL_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
_PACKAGE_SFACE_MODEL = (
    Path(__file__).resolve().parent / "models"
    / "face_recognition_sface_2021dec.onnx"
)
_REPO_SFACE_MODEL = (
    Path(__file__).resolve().parents[2] / "models"
    / "face_recognition_sface_2021dec.onnx"
)
_SFACE_MODEL = _PACKAGE_SFACE_MODEL if _PACKAGE_SFACE_MODEL.is_file() else _REPO_SFACE_MODEL
_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
_DEFAULT_YUNET = _APP_DATA / "RECOGNI" / "models" / "face_detection_yunet_2023mar.onnx"


class RecognitionError(RuntimeError):
    """Raised when local face analysis cannot start or decode the video."""


@dataclass(frozen=True)
class FaceDetection:
    timestamp_seconds: float
    box: tuple[float, float, float, float]
    confidence: float
    character_id: str
    scene_indices: tuple[int, ...]


@dataclass(frozen=True)
class CharacterCandidate:
    character_id: str
    detections: tuple[FaceDetection, ...]
    first_seen_seconds: float
    last_seen_seconds: float


def _ensure_yunet_model(path: Path) -> Path:
    if path.is_file() and path.stat().st_size > 100_000:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    try:
        request = urllib.request.Request(_MODEL_URL, headers={"User-Agent": "RECOGNI"})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if temporary.stat().st_size < 100_000:
            raise RecognitionError("The YuNet model download was incomplete.")
        temporary.replace(path)
    except (OSError, TimeoutError) as exc:
        temporary.unlink(missing_ok=True)
        raise RecognitionError(
            "YuNet face detector is missing and could not be downloaded. "
            "Connect to the internet once or provide its ONNX file."
        ) from exc
    return path


def _unit_vector(value: np.ndarray) -> np.ndarray:
    vector = np.asarray(value, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm) or norm == 0:
        raise RecognitionError("SFace returned an invalid face embedding.")
    return vector / norm


def _scene_indices(timestamp: float, scenes: Iterable[object] | None) -> tuple[int, ...]:
    if scenes is None:
        return ()
    scene_list = tuple(scenes)
    if not scene_list:
        return ()
    final_end = float(getattr(scene_list[-1], "end_seconds"))
    matches = []
    for index, scene in enumerate(scene_list, start=1):
        start = float(getattr(scene, "start_seconds"))
        end = float(getattr(scene, "end_seconds"))
        if start <= timestamp < end or (timestamp == end and end == final_end):
            matches.append(index)
    return tuple(matches)


def analyze_video(
    video_path: str | Path,
    *,
    sample_interval_seconds: float = 2.0,
    similarity_threshold: float = 0.42,
    scenes: Iterable[object] | None = None,
    sface_model_path: str | Path = _SFACE_MODEL,
    yunet_model_path: str | Path = _DEFAULT_YUNET,
    progress: Callable[[float], None] | None = None,
) -> list[CharacterCandidate]:
    """Sample frames, detect faces, embed with SFace, and greedily cluster by cosine similarity.

    The interval controls model inference frequency; OpenCV still decodes the
    video sequentially. Thresholds are provisional and should be reviewed on
    representative movies before being presented as accuracy guarantees.
    """
    video = Path(video_path).expanduser().resolve()
    sface_path = Path(sface_model_path)
    if sample_interval_seconds <= 0:
        raise ValueError("sample_interval_seconds must be greater than zero.")
    if not 0 < similarity_threshold < 1:
        raise ValueError("similarity_threshold must be between zero and one.")
    if not video.is_file():
        raise RecognitionError("The selected video file no longer exists.")
    if not sface_path.is_file():
        raise RecognitionError(f"SFace model was not found: {sface_path}")

    detector_path = _ensure_yunet_model(Path(yunet_model_path))
    try:
        detector = cv2.FaceDetectorYN.create(
            str(detector_path), "", (320, 320), 0.85, 0.3, 5000
        )
        recognizer = cv2.FaceRecognizerSF.create(str(sface_path), "")
    except cv2.error as exc:
        raise RecognitionError(
            "OpenCV could not load the face models. Install opencv-contrib-python "
            "and check that both ONNX files are valid."
        ) from exc

    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RecognitionError("OpenCV could not open the selected video.")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    next_sample = 0.0
    frame_index = 0
    groups: list[dict] = []
    scene_list = tuple(scenes) if scenes is not None else None

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            reported_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0)
            timestamp = reported_ms / 1000 if reported_ms > 0 else (
                frame_index / fps if fps > 0 else 0.0
            )
            frame_index += 1
            if timestamp + 1e-6 < next_sample:
                continue
            next_sample = timestamp + sample_interval_seconds
            height, width = frame.shape[:2]
            detector.setInputSize((width, height))
            _, faces = detector.detect(frame)
            if faces is not None:
                for face in faces:
                    try:
                        aligned = recognizer.alignCrop(frame, face)
                        embedding = _unit_vector(recognizer.feature(aligned))
                    except cv2.error:
                        continue
                    if not groups:
                        group_index = -1
                        best_similarity = -1.0
                    else:
                        scores = [
                            float(np.dot(group["centroid"], embedding))
                            for group in groups
                        ]
                        group_index = int(np.argmax(scores))
                        best_similarity = scores[group_index]
                    if best_similarity < similarity_threshold:
                        groups.append({"centroid": embedding.copy(), "count": 0, "items": []})
                        group_index = len(groups) - 1
                    group = groups[group_index]
                    group["count"] += 1
                    group["centroid"] = _unit_vector(
                        group["centroid"] * (group["count"] - 1) + embedding
                    )
                    x, y, w, h = (float(value) for value in face[:4])
                    item = FaceDetection(
                        timestamp_seconds=round(timestamp, 3),
                        box=(x, y, w, h),
                        confidence=round(float(face[-1]), 4),
                        character_id=f"character-{group_index + 1:03d}",
                        scene_indices=_scene_indices(timestamp, scene_list),
                    )
                    group["items"].append(item)
            if progress and duration > 0:
                progress(min(timestamp / duration, 1.0))
    finally:
        capture.release()

    if progress:
        progress(1.0)
    return [
        CharacterCandidate(
            character_id=f"character-{index:03d}",
            detections=tuple(
                FaceDetection(
                    timestamp_seconds=item.timestamp_seconds,
                    box=item.box,
                    confidence=item.confidence,
                    character_id=f"character-{index:03d}",
                    scene_indices=item.scene_indices,
                )
                for item in group["items"]
            ),
            first_seen_seconds=min(item.timestamp_seconds for item in group["items"]),
            last_seen_seconds=max(item.timestamp_seconds for item in group["items"]),
        )
        for index, group in enumerate(groups, start=1)
        if group["items"]
    ]


def report_dict(video_path: str | Path, candidates: Iterable[CharacterCandidate]) -> dict:
    """Create a JSON-serializable report with source-relative timecodes."""
    return {
        "video": str(Path(video_path).expanduser().resolve()),
        "method": "OpenCV YuNet face detection + SFace embeddings",
        "limitations": [
            "Face-only: people without a detectable face are not included.",
            "Greedy visual clusters are candidates and may split or merge identities.",
            "Review groups and scene assignments before exporting footage.",
        ],
        "characters": [
            {
                "character_id": candidate.character_id,
                "first_seen_seconds": candidate.first_seen_seconds,
                "last_seen_seconds": candidate.last_seen_seconds,
                "detections": [asdict(detection) for detection in candidate.detections],
            }
            for candidate in candidates
        ],
    }


def write_report(
    video_path: str | Path,
    candidates: Iterable[CharacterCandidate],
    output_path: str | Path,
) -> Path:
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report_dict(video_path, candidates), indent=2),
        encoding="utf-8",
    )
    return output
