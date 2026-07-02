"""Modal dialog chrome uses visible borders and scrim."""

from ui.theme import MODAL_BORDER_WIDTH, modal_dialog_kwargs, set_active


def test_modal_dialog_has_border_and_scrim():
    set_active("light")
    params = modal_dialog_kwargs()
    assert params["barrier_color"] == "#66000000"
    assert params["modal"] is True
    assert params["elevation"] == 16
    side = params["shape"].side
    assert side.width == MODAL_BORDER_WIDTH
    assert side.color == "#64748B"