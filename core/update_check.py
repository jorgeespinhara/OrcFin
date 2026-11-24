"""Optional manual update check against GitHub Releases (respects strict_offline)."""

from __future__ import annotations

import json
import re
import urllib.request

from core.branding import APP_VERSION
from core.network_policy import external_calls_allowed
from core.settings_store import load_settings

DEFAULT_GITHUB_REPO = "jorge-rodrigues/OrcFin"


def parse_version(tag: str) -> tuple[int, ...]:
    """Parse semantic version tags like 'v0.2.18' or '0.3.0-beta' into numeric tuples."""
    nums = re.findall(r"\d+", str(tag or ""))
    return tuple(int(n) for n in nums[:4]) if nums else (0,)


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    return parse_version(latest) > parse_version(current)


def check_for_updates(
    repo: str = DEFAULT_GITHUB_REPO,
    *,
    current_version: str = APP_VERSION,
    timeout: float = 5.0,
) -> dict:
    """Check GitHub latest release. Never sends user data; blocked in strict_offline."""
    if not external_calls_allowed(load_settings()):
        return {"status": "offline", "current": current_version}

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"OrcFin/{current_version}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        latest_tag = str(payload.get("tag_name") or "").lstrip("vV").strip()
        html_url = str(payload.get("html_url") or "")
        if not latest_tag:
            return {"status": "error", "current": current_version}
        if is_newer_version(latest_tag, current_version):
            return {
                "status": "update_available",
                "current": current_version,
                "latest": latest_tag,
                "url": html_url,
            }
        return {
            "status": "up_to_date",
            "current": current_version,
            "latest": latest_tag,
            "url": html_url,
        }
    except Exception:
        return {"status": "error", "current": current_version}
