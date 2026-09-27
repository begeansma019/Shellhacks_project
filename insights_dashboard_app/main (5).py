from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

import flet as ft


# =========================================================
# COLORS
# =========================================================

PAGE_BACKGROUND = "#000000"

TEXT_COLOR = ft.Colors.WHITE
SECONDARY_TEXT = ft.Colors.WHITE_60

BORDER_COLOR = ft.Colors.WHITE_12
HOVER_BORDER_COLOR = ft.Colors.WHITE_24

TRANSPARENT = ft.Colors.TRANSPARENT


# =========================================================
# LOCATION DATA
# =========================================================

@dataclass(frozen=True, slots=True)
class LocationOption:
    key: str
    full_label: str
    display_label: str


# =========================================================
# LOCATION SELECTOR
# =========================================================

class ExpandableLocationContainer(ft.Container):
    """
    Transparent location selector.

    Features:
        - No search functionality
        - No location icon
        - Transparent container background
        - Hover to expand
        - City / State / National options
        - Collapses back to the selected option
    """

    HEIGHT = 48
    COLLAPSED_HORIZONTAL_PADDING = 18
    TEXT_SIZE = 14

    _CITY_STATE_SUFFIX = re.compile(
        r",\s*[A-Z]{2}(?:-[A-Z]{2})*\s*$",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        location_name: str = "Fort Pierce, FL",
        state_location: str = "Florida",
        national_location: str = "United States",
        expanded_width: float = 390,
        on_change: Callable[[str], None] | None = None,
    ) -> None:

        self.expanded_width = expanded_width
        self.on_location_change = on_change

        self.selected_key = "city"
        self.expanded = False
        self.hovered_key: str | None = None

        self.locations = self._make_locations(
            location_name,
            state_location,
            national_location,
        )

        # Keep direct references to the text, its opacity layer, and each option.
        #
        # The text itself is always white. A lightweight opacity animation makes
        # it look muted at rest and smoothly brighten to full white on hover.
        self.option_text: dict[str, ft.Text] = {}
        self.option_text_fade: dict[str, ft.Container] = {}
        self.option_containers: dict[str, ft.Container] = {}

        for option in self.locations:
            # Keep the glyph color fixed at white. Only opacity changes on hover,
            # which is cheaper and smoother than repeatedly changing text color
            # or font weight.
            text = ft.Text(
                option.display_label,
                size=self.TEXT_SIZE,
                color=TEXT_COLOR,
                weight=ft.FontWeight.W_500,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
            )

            text_fade = ft.Container(
                alignment=ft.Alignment.CENTER,
                opacity=0.55,
                animate_opacity=ft.Animation(
                    110,
                    ft.AnimationCurve.EASE_OUT,
                ),
                content=text,
            )

            container = ft.Container(
                alignment=ft.Alignment.CENTER,
                opacity=0,
                width=0,
                padding=0,
                animate_opacity=ft.Animation(
                    160,
                    ft.AnimationCurve.EASE_OUT,
                ),
                animate_size=ft.Animation(
                    220,
                    ft.AnimationCurve.EASE_OUT_CUBIC,
                ),
                on_click=lambda e, key=option.key: self.select_location(key),
                on_hover=lambda e, key=option.key: self._handle_option_hover(
                    key,
                    e,
                ),
                content=text_fade,
            )

            self.option_text[option.key] = text
            self.option_text_fade[option.key] = text_fade
            self.option_containers[option.key] = container

        self.options_row = ft.Row(
            expand=True,
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                self.option_containers["city"],
                self.option_containers["state"],
                self.option_containers["national"],
            ],
        )

        super().__init__(
            width=self._collapsed_width(),
            height=self.HEIGHT,

            # The selector itself stays transparent.
            bgcolor=TRANSPARENT,

            border=ft.Border.all(
                width=1,
                color=BORDER_COLOR,
            ),
            border_radius=15,

            padding=ft.Padding.symmetric(
                horizontal=self.COLLAPSED_HORIZONTAL_PADDING,
            ),

            alignment=ft.Alignment.CENTER,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,

            animate=ft.Animation(
                260,
                ft.AnimationCurve.EASE_OUT_CUBIC,
            ),

            on_hover=self._handle_hover,
            content=self.options_row,
        )

        self._sync(refresh=False)

    # =====================================================
    # DATA
    # =====================================================

    @classmethod
    def _city_display_name(cls, value: str) -> str:
        """
        Turns:
            Fort Pierce, FL
        into:
            Fort Pierce
        """
        cleaned = cls._CITY_STATE_SUFFIX.sub("", value).strip()
        return cleaned or value.strip()

    @classmethod
    def _make_locations(
        cls,
        city: str,
        state: str,
        national: str,
    ) -> tuple[LocationOption, ...]:

        city = city.strip()
        state = state.strip()
        national = national.strip()

        return (
            LocationOption(
                key="city",
                full_label=city,
                display_label=cls._city_display_name(city),
            ),
            LocationOption(
                key="state",
                full_label=state,
                display_label=state,
            ),
            LocationOption(
                key="national",
                full_label=national,
                display_label=national,
            ),
        )

    def _location_by_key(self, key: str) -> LocationOption:
        for option in self.locations:
            if option.key == key:
                return option

        raise KeyError(key)

    # =====================================================
    # WIDTH
    # =====================================================

    def _estimate_text_width(self, value: str) -> float:
        """
        Simple width estimate so the collapsed pill fits the selected text.
        """
        return max(
            55,
            (len(value) * self.TEXT_SIZE * 0.57)
            + (self.COLLAPSED_HORIZONTAL_PADDING * 2),
        )

    def _collapsed_width(self) -> float:
        selected = self._location_by_key(self.selected_key)

        return min(
            self._estimate_text_width(selected.display_label),
            self.expanded_width,
        )

    # =====================================================
    # INTERACTION
    # =====================================================

    @staticmethod
    def _is_hovered(event: ft.ControlEvent) -> bool:
        return event.data is True or str(event.data).lower() == "true"

    def _handle_hover(self, event: ft.ControlEvent) -> None:
        self.expanded = self._is_hovered(event)

        if not self.expanded:
            self.hovered_key = None

        self._sync()

    def _handle_option_hover(
        self,
        key: str,
        event: ft.ControlEvent,
    ) -> None:
        hovered = self._is_hovered(event)
        self.hovered_key = key if hovered else None
        self._sync()

    def select_location(self, key: str) -> None:

        valid_keys = {option.key for option in self.locations}

        if key not in valid_keys:
            return

        changed = key != self.selected_key

        self.selected_key = key

        # Keep the container expanded while the mouse is still inside it.
        self._sync()

        if changed and self.on_location_change is not None:
            self.on_location_change(key)

    # =====================================================
    # VISUAL STATE
    # =====================================================

    def _sync(self, refresh: bool = True) -> None:

        # Width changes on hover.
        self.width = (
            self.expanded_width
            if self.expanded
            else self._collapsed_width()
        )

        # IMPORTANT:
        # The LOCATION CONTAINER always remains transparent.
        self.bgcolor = TRANSPARENT

        self.border = ft.Border.all(
            width=1,
            color=(
                HOVER_BORDER_COLOR
                if self.expanded
                else BORDER_COLOR
            ),
        )

        for option in self.locations:

            container = self.option_containers[option.key]
            text_fade = self.option_text_fade[option.key]

            is_selected = option.key == self.selected_key
            is_hovered = option.key == self.hovered_key
            visible = self.expanded or is_selected

            if self.expanded:
                container.expand = 1
                container.width = None
            else:
                container.expand = False
                container.width = (
                    self._collapsed_width()
                    - (self.COLLAPSED_HORIZONTAL_PADDING * 2)
                    if is_selected
                    else 0
                )

            # This opacity controls whether the option itself is shown.
            container.opacity = 1 if visible else 0

            # This second opacity controls only the text brightness.
            #
            # White at ~55% opacity reads as grey on the black background.
            # Hovering interpolates it to 100% white over 110 ms.
            # The selected item is a little brighter while idle, but hover is
            # still the only state that reaches full opacity.
            text_fade.opacity = (
                1.0
                if is_hovered
                else 0.72
                if is_selected
                else 0.55
            )

        if refresh:
            self.update()

    # =====================================================
    # OPTIONAL EXTERNAL UPDATE
    # =====================================================

    def set_locations(
        self,
        location_name: str,
        state_location: str,
        national_location: str,
        selected_key: str | None = None,
    ) -> None:

        self.locations = self._make_locations(
            location_name,
            state_location,
            national_location,
        )

        if selected_key in {"city", "state", "national"}:
            self.selected_key = selected_key

        for option in self.locations:
            self.option_text[option.key].value = option.display_label

        self._sync()


# =========================================================
# MAIN APP
# =========================================================

def main(page: ft.Page) -> None:

    page.title = "Location Selector"
    page.theme_mode = ft.ThemeMode.DARK

    # IMPORTANT:
    # The PAGE is black so the transparent selector is visible.
    # Only the selector itself is transparent.
    page.bgcolor = PAGE_BACKGROUND

    page.padding = 30

    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    # -----------------------------------------------------
    # LOCATION VALUES
    # -----------------------------------------------------

    location_labels = {
        "city": "Fort Pierce, FL",
        "state": "Florida",
        "national": "United States",
    }

    selected_text = ft.Text(
        "Selected location: Fort Pierce, FL",
        size=14,
        color=SECONDARY_TEXT,
    )

    # -----------------------------------------------------
    # CALLBACK
    # -----------------------------------------------------

    def location_changed(key: str) -> None:
        selected_text.value = (
            f"Selected location: {location_labels[key]}"
        )
        page.update()

    # -----------------------------------------------------
    # LOCATION SELECTOR
    # -----------------------------------------------------

    location_selector = ExpandableLocationContainer(
        location_name=location_labels["city"],
        state_location=location_labels["state"],
        national_location=location_labels["national"],
        expanded_width=390,
        on_change=location_changed,
    )

    # -----------------------------------------------------
    # UI
    # -----------------------------------------------------

    page.add(
        ft.Column(
            tight=True,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "Location Selector",
                    size=24,
                    color=TEXT_COLOR,
                    weight=ft.FontWeight.W_600,
                ),

                ft.Text(
                    "Hover over the selector to expand it.",
                    size=13,
                    color=SECONDARY_TEXT,
                ),

                # Fixed-width holder keeps the selector's LEFT edge anchored.
                # As the selector width increases, it expands only to the RIGHT.
                ft.Container(
                    width=390,
                    height=ExpandableLocationContainer.HEIGHT,
                    alignment=ft.Alignment.CENTER_LEFT,
                    content=location_selector,
                ),

                selected_text,
            ],
        )
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.WEB_BROWSER,
    )
