"""Dialog stack dismissal (Flet 0.85)."""

from __future__ import annotations

import flet as ft

from ui.shell import OrcFinApp


class _FakeDialog:
    def __init__(self) -> None:
        self.open = True


class _FakeStack:
    def __init__(self) -> None:
        self.controls: list[_FakeDialog] = []

    def update(self) -> None:
        pass


class _FakePage:
    def __init__(self) -> None:
        self._dialogs = _FakeStack()
        self.updated = False

    def _remove_dialog(self, dialog: _FakeDialog) -> None:
        if dialog in self._dialogs.controls:
            self._dialogs.controls.remove(dialog)

    def update(self) -> None:
        self.updated = True


def test_close_modal_removes_top_dialog_only():
    app = object.__new__(OrcFinApp)
    page = _FakePage()
    first = _FakeDialog()
    second = _FakeDialog()
    page._dialogs.controls.extend([first, second])
    app.page = page

    app.close_modal()

    assert first in page._dialogs.controls
    assert first.open is True
    assert second not in page._dialogs.controls
    assert second.open is False
    assert page.updated is True


def test_close_all_modals_clears_stack():
    app = object.__new__(OrcFinApp)
    page = _FakePage()
    page._dialogs.controls.extend([_FakeDialog(), _FakeDialog()])
    app.page = page

    app.close_all_modals()

    assert page._dialogs.controls == []
    assert page.updated is True