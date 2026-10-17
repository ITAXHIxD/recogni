"""RECOGNI desktop entry point."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QLabel, QListWidget, QMainWindow,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)
from recogni.media import MediaMetadata, MediaValidationError, format_duration, probe_video
from recogni.scenes import Scene, SceneDetectionError, detect_scenes


def format_scene_time(seconds: float) -> str:
    """Show millisecond precision so short scene boundaries remain distinguishable."""
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


class MediaWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, operation, *args):
        super().__init__()
        self.operation, self.args = operation, args

    def run(self):
        try:
            self.succeeded.emit(self.operation(*self.args))
        except (MediaValidationError, SceneDetectionError) as exc:
            self.failed.emit(str(exc))
        except Exception:
            self.failed.emit("An unexpected error occurred. Please try again.")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RECOGNI")
        self.resize(1000, 740)
        self.setMinimumSize(760, 560)
        self._thread = None
        self._worker = None
        self._metadata: MediaMetadata | None = None

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        title = QLabel("RECOGNI")
        title.setObjectName("title")
        subtitle = QLabel("Character scene extraction for video editors")
        subtitle.setObjectName("subtitle")

        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_layout.setSpacing(12)
        self.status = QLabel("Ready when you are.")
        self.status.setObjectName("status")
        self.details = QLabel(
            "Choose a local movie to inspect its properties and detect scene cuts.\n"
            "Your source video stays on this computer."
        )
        self.details.setWordWrap(True)
        self.details.setObjectName("details")
        self.select_button = QPushButton("Select movie")
        self.select_button.setObjectName("primaryButton")
        self.select_button.clicked.connect(self.choose_movie)
        self.analyze_button = QPushButton("Detect scenes")
        self.analyze_button.setObjectName("secondaryButton")
        self.analyze_button.setEnabled(False)
        self.analyze_button.clicked.connect(self.analyze_scenes)
        hero_layout.addWidget(self.status)
        hero_layout.addWidget(self.details)
        hero_layout.addWidget(self.select_button)
        hero_layout.addWidget(self.analyze_button)

        heading = QLabel("Detected scenes")
        heading.setObjectName("sectionTitle")
        self.scene_list = QListWidget()
        self.scene_list.setObjectName("sceneList")
        self.scene_list.setMinimumHeight(160)
        footer = QLabel("LOCAL-FIRST • PYTHON • WINDOWS DESKTOP")
        footer.setObjectName("footer")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(hero)
        layout.addWidget(heading)
        layout.addWidget(self.scene_list, 1)
        layout.addWidget(footer)
        self.setCentralWidget(root)
        self.setStyleSheet("""
            QMainWindow, QWidget#root { background: #10151b; color: #e8f0f5; font-family: "Segoe UI"; }
            QLabel#title { font-size: 30px; font-weight: 700; letter-spacing: 2px; color: #e9fbff; }
            QLabel#subtitle, QLabel#footer { color: #8b9ba8; }
            QLabel#subtitle { font-size: 14px; }
            QLabel#footer { font-size: 10px; letter-spacing: 2px; }
            QFrame#hero { background: #171f27; border: 1px solid #2b414c; border-radius: 16px; }
            QLabel#status { font-size: 20px; font-weight: 600; }
            QLabel#details { color: #aebdc7; font-size: 13px; }
            QLabel#sectionTitle { font-size: 17px; font-weight: 600; }
            QPushButton { border: none; border-radius: 8px; padding: 12px 20px; font-weight: 700; }
            QPushButton#primaryButton { background: #77e4dc; color: #102024; }
            QPushButton#primaryButton:hover { background: #a0f4ec; }
            QPushButton#secondaryButton { background: #263b45; color: #d8f7f5; border: 1px solid #42636b; }
            QPushButton:disabled { background: #29343b; color: #75848c; }
            QListWidget#sceneList { background: #171f27; border: 1px solid #2b414c; border-radius: 10px; padding: 8px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #26343d; }
        """)

    def choose_movie(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a movie", str(Path.home()),
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg);;All files (*)",
        )
        if not path:
            return
        self._metadata = None
        self.scene_list.clear()
        self.analyze_button.setEnabled(False)
        self._set_busy("Validating movie…", "Reading media metadata locally.")
        self._start_worker(probe_video, (Path(path),), self._show_metadata)

    def analyze_scenes(self):
        if self._metadata is None:
            return
        self.scene_list.clear()
        self._set_busy(
            "Detecting scene cuts…",
            "Scanning locally with FFmpeg. This detects visual cuts, not character identities.",
        )
        self._start_worker(
            detect_scenes, (self._metadata.path, self._metadata.duration_seconds),
            self._show_scenes,
        )

    def _set_busy(self, status, details):
        self.status.setText(status)
        self.details.setText(details)
        self.select_button.setEnabled(False)
        self.analyze_button.setEnabled(False)

    def _start_worker(self, operation, args, on_success):
        self._thread = QThread(self)
        self._worker = MediaWorker(operation, *args)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(on_success)
        self._worker.failed.connect(self._show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._worker_finished)
        self._thread.start()

    def _show_metadata(self, metadata: MediaMetadata):
        self._metadata = metadata
        fps = f"{metadata.frame_rate:.3f} fps" if metadata.frame_rate else "Unknown"
        self.status.setText("Movie validated")
        self.details.setText(
            f"File: {metadata.path.name}\nDuration: {format_duration(metadata.duration_seconds)} "
            f"({metadata.duration_seconds:.2f} seconds)\nResolution: {metadata.width} × {metadata.height}\n"
            f"Frame rate: {fps}\nAudio: {'Present' if metadata.has_audio else 'Not detected'}\n"
            f"Container: {metadata.format_name}\n\nScene detection is ready. Character identification comes next."
        )

    def _show_scenes(self, scenes: list[Scene]):
        for i, scene in enumerate(scenes, 1):
            self.scene_list.addItem(
                f"Scene {i:03d}    {format_scene_time(scene.start_seconds)} → "
                f"{format_scene_time(scene.end_seconds)}    ({scene.duration_seconds:.2f} s)"
            )
        self.status.setText(f"Scene detection complete · {len(scenes)} scenes")
        self.details.setText("Review the timestamps before editing. Rapid flashes may create extra cuts.")

    def _show_error(self, message: str):
        self.status.setText("Operation failed")
        self.details.setText(message)
        QMessageBox.warning(self, "RECOGNI", message)

    def _worker_finished(self):
        self.select_button.setEnabled(True)
        self.analyze_button.setEnabled(self._metadata is not None)
        self._worker = None
        self._thread = None


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("RECOGNI")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
