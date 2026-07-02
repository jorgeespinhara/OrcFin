"""Dialog stack dismissal."""

from __future__ import annotations

import flet as ft

from ui.shell import OrcFinApp


class _FakeDialog(ft.AlertDialog):
    def __init__(self) -> None:
        super().__init__(open=True)


class _FakePage:
    def __init__(self) -> None:
        self.updated = False

    def update(self) -> None:
        self.updated = True

    def show_dialog(self, _dialog: ft.AlertDialog) -> None:
        pass


def test_close_modal_removes_top_dialog_only():
    app = object.__new__(OrcFinApp)
    first = _FakeDialog()
    second = _FakeDialog()
    app._open_dialogs = [first, second]
    app.page = _FakePage()

    app.close_modal()

    assert app._open_dialogs == [first]
    assert first.open is True
    assert second.open is False
    assert app.page.updated is True


def test_close_all_modals_clears_stack():
    app = object.__new__(OrcFinApp)
    first = _FakeDialog()
    second = _FakeDialog()
    app._open_dialogs = [first, second]
    app.page = _FakePage()

    app.close_all_modals()

    assert app._open_dialogs == []
    assert first.open is False
    assert second.open is False
    assert app.page.updated is True