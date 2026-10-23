# RECOGNI desktop architecture

## Product constraint

RECOGNI is a native Windows desktop application written in Python. It must not depend on a website, browser UI, localhost web server, cloud database, or mandatory account for its core workflow.

Default workflow: select a local movie → validate it → analyze locally → review character and scene groups → select scenes → export local compilations.

## Recommended stack

- **GUI:** PySide6 (Qt for Python).
- **Runtime:** Python 3.11+ initially; pin and test supported versions before packaging.
- **Media inspection and rendering:** FFprobe and FFmpeg invoked with safe argument lists, never shell-interpolated commands.
- **Local persistence:** SQLite for projects, analysis records, corrections, and export manifests.
- **Media/cache storage:** user-selected local folders with bounded caches and cleanup controls.
- **AI runtime:** evaluate CPU-friendly ONNX Runtime/PyTorch-compatible detectors and embeddings; optional acceleration only when available.
- **Optional providers:** adapters for local Ollama and remote Gemini can be added behind a common interface. Remote processing must be opt-in and disclose what media context will be sent.
- **Packaging:** package a Windows executable only after the source workflow and dependency/model licenses are verified.

## Module boundaries

- recogni.main: application entry point and Qt window.
- recogni.media: safe media validation, FFprobe metadata, frame extraction, and FFmpeg operations.
- recogni.jobs: background tasks, progress events, cancellation, and job lifecycle.
- recogni.analysis: scene detection, sampling strategy, and character-to-scene association.
- recogni.ai: detector, embedding, tracking, clustering, and provider adapter interfaces.
- recogni.storage: SQLite schema, project persistence, and cache index.
- recogni.export: chronological clip assembly, audio settings, output verification, and source-timecode manifest.

Keep long-running tasks outside the UI thread. Each layer should be testable independently, and model implementations should be replaceable without rewriting the desktop interface.

## Analysis and export flow

1. Select a local video through a native file dialog.
2. Validate file existence, extension, readability, and actual media streams with FFprobe.
3. Show duration, resolution, frame rate, and audio availability.
4. Sample frames efficiently and detect scene/shot boundaries.
5. Sample frames, run YuNet face detection and SFace embeddings, and greedily group similar embeddings into provisional candidates.
6. Associate character candidates with time ranges and expose uncertainty for human review.
7. Let the editor rename, merge, split, add, or remove character-scene assignments.
8. Assemble selected scenes in chronological order with configurable padding and audio behavior.
9. Verify the resulting video can be opened and write a manifest mapping output segments to original source timecodes.

Do not treat face detection, short-term tracking, cross-scene identity, scene detection, and clip rendering as one interchangeable task.

## Privacy and reliability

- Keep source movies, face/person features, analysis metadata, and exports local by default.
- Never upload a movie or frame to a remote provider without explicit consent.
- Never require a paid API key for the core local workflow.
- Do not put API keys or private media paths into logs unnecessarily.
- Do not modify source videos.
- Validate subprocess arguments and handle timeouts, missing FFmpeg tools, damaged files, and malformed model output.
- Preserve completed analysis when an export fails; make jobs cancellable and retryable.
- Report success only after verifying the output file exists and is readable.
- Keep memory use bounded and provide CPU fallback; do not assume CUDA or dedicated VRAM.

## Initial milestone

The initial code adds a PySide6 shell, local file selection, background FFprobe inspection, and user-visible metadata/errors. It is only the media-ingestion foundation, not an AI MVP yet.

Next milestones:

1. Test and harden media validation on representative files.
2. Add frame sampling and scene-boundary detection.
3. Benchmark sampled-frame face detection and embedding thresholds on CPU; current clustering is provisional.
4. Implement character grouping and correction controls.
5. Add scene preview/selection and verified chronological exports.
6. Package for Windows and document model licenses, cache management, and limitations.

## Current non-goals

- No React/TypeScript web frontend.
- No FastAPI service or localhost web server.
- No PostgreSQL, Redis, or S3 requirement.
- No mandatory login or cloud storage.
- No claim of perfect character recognition.
