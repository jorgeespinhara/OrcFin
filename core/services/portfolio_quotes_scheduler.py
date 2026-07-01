"""Background portfolio quote refresh (default 15 minutes)."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from core.db.repositories.investment_holdings import get_holdings
from core.services.portfolio_service import quotes_enabled, refresh_quotes

if TYPE_CHECKING:
    from ui.shell import OrcFinApp

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_MINUTES = 15


def quote_interval_seconds(settings: dict | None) -> int:
    minutes = 15
    if settings:
        try:
            minutes = int(settings.get("portfolio_quote_refresh_minutes", 15))
        except (TypeError, ValueError):
            minutes = 15
    return max(5, min(60, minutes)) * 60


async def run_portfolio_quote_scheduler(app: "OrcFinApp") -> None:
    """Refresh portfolio quotes periodically while the app is open."""
    await asyncio.sleep(5)
    while True:
        try:
            _refresh_portfolio_quotes(app)
        except Exception as ex:
            logger.debug("portfolio quote refresh failed: %s", ex)
        await asyncio.sleep(quote_interval_seconds(app.settings))


def _refresh_portfolio_quotes(app: "OrcFinApp") -> None:
    if app.is_mei_mode() or not quotes_enabled(app.settings):
        return
    if app.is_consolidated:
        return
    profile_id = app.get_view_profile_id()
    if not profile_id:
        return
    if not get_holdings(profile_id):
        return

    def work() -> None:
        try:
            refresh_quotes(profile_id, app.settings)
        except Exception as ex:
            logger.debug("quote refresh failed: %s", ex)
            return
        if app.active_view_index() in (0, 3):
            app.refresh_current_view()

    app.page.run_thread(work)


def start_portfolio_quote_scheduler(app: "OrcFinApp") -> None:
    async def _loop() -> None:
        await run_portfolio_quote_scheduler(app)

    app.page.run_task(_loop)