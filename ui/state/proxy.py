"""Exposes AppState fields on the app shell for view access."""

from __future__ import annotations

# Forwarded to self.state — see _STATE_FIELDS and _STATE_METHODS below.
_STATE_FIELDS = frozenset({
    "current_view_index",
    "mei_view_index",
    "selected_profile_id",
    "is_consolidated",
    "app_mode",
    "filter_year",
    "filter_month",
    "projection_months_ahead",
    "profiles",
})

_STATE_METHODS = frozenset({
    "active_view_index",
    "set_active_view_index",
    "enter_mei_shell",
    "enter_personal_shell",
    "get_view_profile_id",
    "is_mei_mode",
    "get_view_context_label",
    "set_period_filter",
    "set_projection_months_ahead",
    "save_settings",
    "reset_after_wipe",
})


class StateProxyMixin:
    """Mixin for OrcFinApp — views use app.selected_profile_id and related state."""

    def __getattr__(self, name: str):
        if name in _STATE_FIELDS or name in _STATE_METHODS:
            return getattr(self.state, name)
        raise AttributeError(f"{type(self).__name__!r} has no attribute {name!r}")

    def __setattr__(self, name: str, value) -> None:
        if name == "state" or not object.__getattribute__(self, "__dict__").get("state"):
            object.__setattr__(self, name, value)
            return
        if name in _STATE_FIELDS:
            setattr(self.state, name, value)
            return
        object.__setattr__(self, name, value)

    def ensure_individual_profile(self) -> int | None:
        pid = self.state.ensure_individual_profile()
        if pid and not self.state.is_mei_mode() and hasattr(self, "profile_dropdown"):
            self.profile_dropdown.value = str(pid)
        return pid