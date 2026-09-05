"""The Stats screen: retention, review history, forecast, and JLPT progress."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from kanji_app.core.models import CardState
from kanji_app.services.stats import DayCount, JlptProgress, StatsReport
from kanji_app.ui.view_models.stats_vm import StatsViewModel
from kanji_app.ui.widgets.bar_chart import Bar, BarChart

_STATE_ORDER = (CardState.NEW, CardState.LEARNING, CardState.RELEARNING, CardState.REVIEW)


class StatsView(QWidget):
    def __init__(self, vm: StatsViewModel) -> None:
        super().__init__()
        self._vm = vm

        self._headline = QLabel()
        headline_font = self._headline.font()
        headline_font.setPointSize(15)
        self._headline.setFont(headline_font)

        self._retention = QLabel()
        self._breakdown = QLabel()

        self._history = BarChart(accent="#3a7bd5")
        self._forecast = BarChart(accent="#c0392b")

        self._jlpt_box = QVBoxLayout()

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(self._headline)
        layout.addWidget(self._retention)
        layout.addWidget(self._breakdown)
        layout.addWidget(_section("Reviews per day (last 3 weeks)"))
        layout.addWidget(self._history)
        layout.addWidget(_section("Coming due (next 2 weeks)"))
        layout.addWidget(self._forecast)
        layout.addWidget(_section("JLPT progress"))
        layout.addLayout(self._jlpt_box)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._vm.changed.connect(self._render)
        self._render()

    def refresh(self) -> None:
        self._vm.refresh()

    def _render(self) -> None:
        report = self._vm.report
        self._headline.setText(
            f"{report.total_cards} cards  ·  {report.streak_days}-day streak  ·  "
            f"{report.reviewed_today} reviewed today"
        )
        self._retention.setText(_retention_text(report))
        self._breakdown.setText(_breakdown_text(report))
        self._history.set_bars([_bar(d) for d in report.history])
        self._forecast.set_bars([_bar(d) for d in report.forecast])
        self._rebuild_jlpt(report.jlpt)

    def _rebuild_jlpt(self, rows: list[JlptProgress]) -> None:
        while self._jlpt_box.count():
            item = self._jlpt_box.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()

        for row in rows:
            container = QWidget()
            form = QFormLayout(container)
            bar = QProgressBar()
            bar.setMaximum(row.total)
            bar.setValue(row.learned)
            bar.setFormat(f"{row.learned} / {row.total} learned  ({row.in_deck} in deck)")
            form.addRow(f"N{row.level}", bar)
            self._jlpt_box.addWidget(container)


def _bar(day: DayCount) -> Bar:
    return Bar(label=str(day.day.day), value=day.count)


def _retention_text(report: StatsReport) -> str:
    if report.retention is None:
        return "Retention: not enough reviews yet"
    return (
        f"Retention: {report.retention * 100:.0f}%  "
        f"({report.mature_reviews} mature review{'' if report.mature_reviews == 1 else 's'})"
    )


def _breakdown_text(report: StatsReport) -> str:
    parts = [
        f"{report.state_breakdown.get(state, 0)} {state.value}"
        for state in _STATE_ORDER
        if report.state_breakdown.get(state, 0)
    ]
    return "  ·  ".join(parts) or "No cards yet"


def _section(text: str) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label
