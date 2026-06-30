"""Application bootstrap and Flet window setup."""

from ui.shell import OrcFinApp


def start(page) -> OrcFinApp:
    """Launch the OrcFin shell on a Flet page."""
    return OrcFinApp(page)