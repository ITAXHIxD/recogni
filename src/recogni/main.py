"""Entry point and first native RECOGNI desktop workflow."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (\n    QListWidget,
    QApplication,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from recogni.media import MediaMetadata, MediaValidationError, format_duration, probe_video\nfrom recogni.scenes import Scene, SceneDetectionError, detect_scenes


class ProbeWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def run(self) -> None:
        try:
            self.succeeded.emit(probe_video(self.path))
        except MediaValidationError as exc:
            self.failed.emit(str(exc))
        except Exception:
            # Avoid exposing tracebacks in the user-facing UI; diagnostics can be
            # added through structured local logging as the application grows.
            self.failed.emit("An unexpected error occurred while inspecting this video.")
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RECOGNI")
        self.resize(960, 640)
        self.setMinimumSize(760, 520)
        self._thread: QThread | None = None
        self._worker: QObject | None = None\n        self._metadata: MediaMetadata | None = None

        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

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
            "Choose a local movie to validate it and inspect its media properties.\n"
            "Your source video is not uploaded or modified."
        )
        self.details.setWordWrap(True)
        self.details.setObjectName("details")

        self.select_button = QPushButton("Select movie")
        self.select_button.setObjectName("primaryButton")
        self.select_button.clicked.connect(self.choose_movie)

        hero_layout.addWidget(self.status)
        hero_layout.addWidget(self.details)
        hero_layout.addSpacing(8)
        self.analyze_button = QPushButton("Detect scenes")\n        self.analyze_button.setObjectName("secondaryButton")\n        self.analyze_button.setEnabled(False)\n        self.analyze_button.clicked.connect(self.analyze_scenes)\n        hero_layout.addWidget(self.select_button, 0)\n        hero_layout.addWidget(self.analyze_button, 0)\n\n        self.scene_heading = QLabel("Detected scenes")\n        self.scene_heading.setObjectName("sectionTitle")\n        self.scene_list = QListWidget()\n        self.scene_list.setObjectName("sceneList")\n        self.scene_list.setMinimumHeight(150)

        footer = QLabel("LOCAL-FIRST • PYTHON • WINDOWS DESKTOP")
        footer.setObjectName("footer")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(12)
        layout.addWidget(hero)
        layout.addStretch(1)
        layout.addWidget(footer)
        self.setCentralWidget(root)

        self.setStyleSheet("""
            QMainWindow, QWidget#root {
                background: #10151b;
                color: #e8f0f5;
                font-family: "Segoe UI";
            }
            QLabel#title {
                font-size: 30px;
                font-weight: 700;
                letter-spacing: 2px;
                color: #e9fbff;
            }
            QLabel#subtitle, QLabel#footer { color: #8b9ba8; }
            QLabel#subtitle { font-size: 14px; }
            QLabel#footer { font-size: 10px; letter-spacing: 2px; }
            QFrame#hero {
                background: #171f27;
                border: 1px solid #2b414c;
                border-radius: 16px;
            }
            QLabel#status { font-size: 20px; font-weight: 600; }
            QLabel#details { color: #aebdc7; font-size: 13px; }
            QPushButton#primaryButton {
                background: #77e4dc;
                color: #102024;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: 700;
                min-width: 130px;
            }
            QPushButton#primaryButton:hover { background: #a0f4ec; }\n            QPushButton#secondaryButton { background: #263b45; color: #d8f7f5; border: 1px solid #42636b; }\n            QLabel#sectionTitle { font-size: 17px; font-weight: 600; }\n            QListWidget#sceneList { background: #171f27; border: 1px solid #2b414c; border-radius: 10px; padding: 8px; }\n            QListWidget::item { padding: 8px; border-bottom: 1px solid #26343d; }
            QPushButton#primaryButton:disabled {
                background: #41575b;
                color: #aebdc7;
            }
        """)

    def choose_movie(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a movie",
            str(Path.home()),
            "Video files (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg);;All files (*)",
        )
        if not path:
            return

        self.select_button.setEnabled(False)
        self.status.setText("Validating movie…")
        self.details.setText("Reading media metadata locally. The window will remain responsive.")

        self._thread = QThread(self)
        self._worker = ProbeWorker(Path(path))
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self.show_metadata)
        self._worker.failed.connect(self.show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._probe_finished)
        self._thread.start()

    def show_metadata(self, metadata: MediaMetadata) -> None:
        fps = f"{metadata.frame_rate:.3f} fps" if metadata.frame_rate else "Unknown frame rate"
        audio = "Present" if metadata.has_audio else "Not detected"
        self.status.setText("Movie validated")
        self.details.setText(
            f"File: {metadata.path.name}\n"
            f"Duration: {format_duration(metadata.duration_seconds)} "
            f"({metadata.duration_seconds:.2f} seconds)\n"
            f"Resolution: {metadata.width} × {metadata.height}\n"
            f"Frame rate: {fps}\n"
            f"Audio: {audio}\n"
            f"Container: {metadata.format_name}\n\n"
            "This is the first working milestone. Scene and character analysis are not "
            "implemented yet."
        )

    def show_error(self, message: str) -> None:
        self.status.setText("Movie validation failed")
        self.details.setText(message)
        QMessageBox.warning(self, "Could not validate movie", message)

    def _probe_finished(self) -> None:
        self.select_button.setEnabled(True)
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
