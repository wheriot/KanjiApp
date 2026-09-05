"""A minimal, theme-aware vertical bar chart drawn with QPainter.

Deliberately tiny — enough for "reviews per day" and "due forecast". No external
charting dependency.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget


@dataclass(frozen=True, slots=True)
class Bar:
    label: str
    value: float


class BarChart(QWidget):
    def __init__(self, accent: str = "#3a7bd5") -> None:
        super().__init__()
        self._bars: list[Bar] = []
        self._accent = QColor(accent)
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_bars(self, bars: list[Bar]) -> None:
        self._bars = bars
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        if not self._bars:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        ink = self.palette().color(self.foregroundRole())
        faint = QColor(ink)
        faint.setAlpha(90)

        label_h = 16
        top_pad = 4
        plot = QRectF(0, top_pad, self.width(), self.height() - label_h - top_pad)
        peak = max((b.value for b in self._bars), default=0) or 1
        slot = plot.width() / len(self._bars)
        bar_w = min(slot * 0.6, 28)

        painter.setPen(faint)
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))

        for i, bar in enumerate(self._bars):
            cx = plot.left() + slot * (i + 0.5)
            height = (bar.value / peak) * plot.height()
            rect = QRectF(cx - bar_w / 2, plot.bottom() - height, bar_w, height)
            painter.fillRect(rect, self._accent if bar.value else faint)

            painter.setPen(faint if i % 2 else ink)
            painter.drawText(
                QRectF(plot.left() + slot * i, plot.bottom() + 1, slot, label_h),
                Qt.AlignmentFlag.AlignCenter,
                bar.label,
            )
