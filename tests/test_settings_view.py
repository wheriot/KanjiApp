from __future__ import annotations

from kanji_app.services.settings import AppSettings
from kanji_app.services.study import StudyService
from kanji_app.ui.app import build_app
from kanji_app.ui.view_models.settings_vm import SettingsViewModel
from kanji_app.ui.views.credits import CREDITS_HTML, CreditsDialog
from kanji_app.ui.views.settings_view import SettingsView


def test_settings_vm_persists_changes(study_service: StudyService) -> None:
    vm = SettingsViewModel(study_service)

    themes: list[str] = []
    vm.theme_changed.connect(themes.append)
    vm.set_theme("dark")
    vm.set_retention(0.92)

    assert themes == ["dark"]
    assert study_service.settings.theme == "dark"
    assert study_service.settings.fsrs_retention == 0.92


def test_settings_view_builds_and_shows_current_values(study_service: StudyService) -> None:
    build_app([])
    study_service.update_settings(AppSettings(theme="light", fsrs_retention=0.88))
    view = SettingsView(SettingsViewModel(study_service))
    assert view._theme.currentData() == "light"
    assert view._retention.value() == 0.88


def test_credits_dialog_has_attribution() -> None:
    build_app([])
    CreditsDialog()  # constructs without error
    assert "KANJIDIC2" in CREDITS_HTML
    assert "KanjiVG" in CREDITS_HTML
    assert "CC BY-SA" in CREDITS_HTML
