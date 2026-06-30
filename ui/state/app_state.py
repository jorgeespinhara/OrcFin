"""Navigation, filters, and profile selection for the app shell."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, List, Optional

from core.db.repositories.mei import get_mei_profile
from core.models import Profile, ProfileType


@dataclass
class AppState:
    """Navigation, filters, and profile selection."""

    settings: dict
    profiles: List[Profile] = field(default_factory=list)
    current_view_index: int = 0
    mei_view_index: int = 0
    selected_profile_id: Optional[int] = None
    is_consolidated: bool = True
    app_mode: str = "personal"
    filter_year: int = field(default_factory=lambda: date.today().year)
    filter_month: Optional[int] = None
    projection_months_ahead: int = 3
    on_settings_changed: Optional[Callable[[], None]] = None

    @classmethod
    def from_settings(cls, settings: dict) -> AppState:
        today = date.today()
        filter_year = settings.get("filter_year") or today.year
        state = cls(
            settings=settings,
            selected_profile_id=settings.get("selected_profile_id"),
            app_mode=settings.get("app_mode", "personal"),
            filter_year=filter_year,
            filter_month=settings.get("filter_month"),
            projection_months_ahead=max(
                1, min(12, int(settings.get("projection_months_ahead") or 3))
            ),
        )
        if settings.get("filter_year") is None:
            settings["filter_year"] = filter_year
        return state

    def save_settings(self) -> None:
        self.settings["selected_profile_id"] = self.selected_profile_id
        self.settings["app_mode"] = self.app_mode
        self.settings["filter_year"] = self.filter_year
        self.settings["filter_month"] = self.filter_month
        self.settings["projection_months_ahead"] = self.projection_months_ahead
        if self.on_settings_changed:
            self.on_settings_changed()

    def active_view_index(self) -> int:
        return self.mei_view_index if self.app_mode == "mei" else self.current_view_index

    def set_active_view_index(self, index: int) -> None:
        if self.app_mode == "mei":
            self.mei_view_index = index
        else:
            self.current_view_index = index

    def is_mei_mode(self) -> bool:
        return self.app_mode == "mei"

    def ensure_individual_profile(self) -> Optional[int]:
        if self.app_mode == "mei":
            mei = get_mei_profile()
            return mei.id if mei else None
        if self.selected_profile_id and any(
            p.id == self.selected_profile_id for p in self.profiles
        ):
            return self.selected_profile_id
        if self.profiles:
            self.selected_profile_id = self.profiles[0].id
            self.save_settings()
            return self.selected_profile_id
        return None

    def get_view_profile_id(self) -> Optional[int]:
        if self.app_mode == "mei":
            mei = get_mei_profile()
            return mei.id if mei else None
        if self.is_consolidated:
            return None
        return self.ensure_individual_profile()

    def get_view_context_label(self) -> str:
        if self.app_mode == "mei":
            mei = get_mei_profile()
            return f"MEI: {mei.name}" if mei else "Modo MEI"
        if self.is_consolidated:
            return "Visão Consolidada"
        profile_id = self.ensure_individual_profile()
        if profile_id:
            profile = next((p for p in self.profiles if p.id == profile_id), None)
            if profile:
                return f"Perfil: {profile.name}"
        return "Visão Individual"

    def set_period_filter(self, year: int, month: Optional[int]) -> None:
        self.filter_year = year
        self.filter_month = month
        self.save_settings()

    def set_projection_months_ahead(self, months: int) -> None:
        self.projection_months_ahead = max(1, min(12, months))
        self.save_settings()

    def enter_mei_shell(self, *, home: bool = False) -> None:
        self.app_mode = "mei"
        self.is_consolidated = False
        mei = get_mei_profile()
        if mei:
            self.selected_profile_id = mei.id
            self.settings["mei_profile_id"] = mei.id
        if home:
            self.mei_view_index = 0

    def enter_personal_shell(self) -> None:
        self.app_mode = "personal"
        personal = next(
            (p for p in self.profiles if p.profile_type == ProfileType.PERSONAL),
            self.profiles[0] if self.profiles else None,
        )
        if personal:
            self.selected_profile_id = personal.id

    def reset_after_wipe(self, settings: dict) -> None:
        self.settings = settings
        self.app_mode = "personal"
        self.current_view_index = 0
        self.mei_view_index = 0
        self.is_consolidated = True
        self.selected_profile_id = None
        self.filter_year = date.today().year
        self.filter_month = None
        self.projection_months_ahead = 3
        self.settings.pop("recurrence_prompt_dismissed", None)