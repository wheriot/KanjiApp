"""Widget that draws a kanji's stroke order, statically or as an animation."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPaintEvent, QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSizePolicy, QSlider, QVBoxLayout, QWidget

from kanji_app.core import kanjivg
from kanji_app.core.kanjivg import StrokeDrawing

_FRAME_MS = 650


class _Canvas(QWidget):
    """Square drawing surface for the current SVG."""

    def __init__(self, renderer: QSvgRenderer) -> None:
        super().__init__()
        self._renderer = renderer
        self.setMinimumSize(180, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._renderer.isValid():
            return
        side = min(self.width(), self.height())
        box = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._renderer.render(painter, box)


class StrokeOrderWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._drawing: StrokeDrawing | None = None
        self._step = 0  # 0 = whole kanji; 1..n = first n strokes
        self._renderer = QSvgRenderer()

        self._timer = QTimer(self)
        self._timer.setInterval(_FRAME_MS)
        self._timer.timeout.connect(self._advance)

        self._canvas = _Canvas(self._renderer)
        self._play = QPushButton("▶ Play")
        self._play.clicked.connect(self.toggle)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(0)
        self._slider.valueChanged.connect(self._on_slider)

        controls = QHBoxLayout()
        controls.addWidget(self._play)
        controls.addWidget(self._slider, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas, stretch=1)
        layout.addLayout(controls)

        self._sync_controls()

    # -- public API -----------------------------------------------------

    def set_drawing(self, drawing: StrokeDrawing | None) -> None:
        self.stop()
        self._drawing = drawing
        self._step = 0
        self._slider.setMaximum(drawing.stroke_count if drawing else 0)
        self._rebuild()
        self._sync_controls()

    def toggle(self) -> None:
        if self._timer.isActive():
            self.stop()
        else:
            self.play()

    def play(self) -> None:
        if not self._drawing or self._drawing.stroke_count == 0:
            return
        if self._step >= self._drawing.stroke_count:
            self._step = 0
        self._timer.start()
        self._play.setText("❚❚ Pause")

    def stop(self) -> None:
        self._timer.stop()
        self._play.setText("▶ Play")

    # -- internals ----------------------------------------------------

    def _advance(self) -> None:
        if not self._drawing:
            return
        if self._step >= self._drawing.stroke_count:
            self.stop()
            return
        self._set_step(self._step + 1)

    def _on_slider(self, value: int) -> None:
        if value != self._step:
            self.stop()
            self._set_step(value)

    def _set_step(self, step: int) -> None:
        self._step = step
        self._slider.blockSignals(True)
        self._slider.setValue(step)
        self._slider.blockSignals(False)
        self._rebuild()

    def _rebuild(self) -> None:
        if not self._drawing:
            self._renderer.load(QByteArray())
            self._canvas.update()
            return
        ink = self.palette().color(QPalette.ColorRole.WindowText).name()
        svg = kanjivg.render(
            self._drawing,
            upto=None if self._step == 0 else self._step,
            ink=ink,
        )
        self._renderer.load(QByteArray(svg.encode("utf-8")))
        self._canvas.update()

    def _sync_controls(self) -> None:
        has_strokes = bool(self._drawing and self._drawing.stroke_count)
        self._play.setEnabled(has_strokes)
        self._slider.setEnabled(has_strokes)
