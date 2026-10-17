# RECOGNI

RECOGNI is a **native Windows desktop application built with Python** for video editors. It is designed to find recurring characters in long-form videos, group their scenes, and export chronological character-specific compilations.

RECOGNI is not a website. The application uses a local desktop GUI and processes local video files on the user's computer by default.

## Current implementation

The first development milestone provides:

- A native PySide6 desktop window.
- A local movie file picker.
- Video validation and metadata extraction through FFprobe.
- Duration, resolution, frame-rate, audio, and container details.
- Background media inspection so the UI remains responsive.
- Local FFmpeg scene-cut detection with a reviewable, chronological scene interval list.
- Clear errors when media tools are missing or a file cannot be decoded.

**Character recognition, character grouping, scene trimming, and export are not implemented yet.** Scene cuts are visual-change estimates and may need manual review.

## Requirements

- Windows 10/11 (initial target).
- Python 3.11 or newer.
- FFmpeg/FFprobe installed and available on PATH.

## Run from source

Open a terminal in the repository root:

    py -3.11 -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
    python -m recogni.main

If PowerShell blocks virtual-environment activation, run the environment's Python directly:

    .\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"
    .\\.venv\\Scripts\\python.exe -m recogni.main

Check FFprobe installation with:

    ffprobe -version

## Tests

    python -m pytest

## Planned processing architecture

- **Desktop UI:** PySide6.
- **Media tools:** FFmpeg and FFprobe. FFmpeg's scene score is used for the initial scene-cut detector.
- **Local project data:** SQLite and filesystem-based cache.
- **AI/ML pipeline:** pluggable local models for scene detection, person/face detection, tracking, and recurring-character grouping.
- **Provider adapters:** optional integrations such as local Ollama or remote Gemini, clearly marked so users know when media leaves their device.
- **Export:** chronological FFmpeg compilations with a source-timecode manifest.

The AI model choices will be benchmarked on realistic sample videos and ordinary CPU hardware before being treated as final. Basic media processing and export must not require a paid LLM API key.

See the product scope in docs/product-scope.md and architecture in docs/architecture.md.
