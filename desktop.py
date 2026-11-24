"""OrcFin PRO Desktop Launcher — native WebView2 window over local FastAPI + core/."""

from __future__ import annotations

import socket
import threading
import time
import urllib.request

import uvicorn
import webview

from api.server import FRONTEND_DIST, create_app
from core.branding import APP_NAME, APP_VERSION
from core.diagnostics import install_diagnostics_handler


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_ready(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                return
        except Exception:
            time.sleep(0.1)


def main() -> None:
    install_diagnostics_handler()
    if not (FRONTEND_DIST / "index.html").exists():
        raise SystemExit(
            "Build do frontend não encontrado em frontend/dist.\n"
            "Execute: cd frontend && npm install && npm run build"
        )

    port = _find_free_port()
    app = create_app()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    _wait_ready(f"{base_url}/api/meta")

    webview.create_window(
        title=f"{APP_NAME} v{APP_VERSION}",
        url=base_url,
        width=1360,
        height=860,
        min_size=(1024, 680),
        background_color="#070B14",
    )
    webview.start(debug=False)
    server.should_exit = True


if __name__ == "__main__":
    main()
