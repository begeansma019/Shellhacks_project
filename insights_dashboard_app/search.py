import asyncio

import flet as ft


COLLAPSED_WIDTH = 56
EXPANDED_WIDTH = 390
SEARCH_HEIGHT = 56

RESULT_HEIGHT = 60
RESULTS_PADDING = 0
MAX_RESULTS = 6


DEFAULT_OCCUPATIONS = ()


async def main(
    page: ft.Page,
    occupations=None,
    search_provider=None,
    on_select=None,
    mount=True,
    show_selection_text=True,
    collapse_on_select=False,
    search_button_bgcolor=None,
    expanded_search_button_bgcolor=None,
    search_button_icon=None,
    search_result_icon_factory=None,
    clear_button_icon=None,
    search_button_size=SEARCH_HEIGHT,
    search_height=SEARCH_HEIGHT,
    collapsed_width=COLLAPSED_WIDTH,
):
    if mount:
        page.title = "Expandable Search"
        page.bgcolor = ft.Colors.BLACK
        page.padding = 30

        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

    occupation_records = (
        occupations
        if occupations is not None
        else DEFAULT_OCCUPATIONS
    )

    search_expanded = False
    results_open = False
    search_revision = 0

    selected_result_text = ft.Text(
        value="",
        size=15,
        color=ft.Colors.WHITE_70,
    )

    results_column = ft.Column(
        controls=[],
        spacing=0,
        tight=True,
    )

    # The results container always remains mounted.
    # Its height and opacity are animated instead of changing visible.
    results_container = ft.Container(
        width=EXPANDED_WIDTH,
        height=0,
        opacity=0,
        bgcolor="#202124",
        border_radius=18,
        padding=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(
            duration=220,
            curve=ft.AnimationCurve.EASE_OUT,
        ),
        animate_opacity=ft.Animation(
            duration=260,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),
        content=results_column,
    )

    def filter_results(query: str) -> list[dict[str, str]]:
        normalized_query = query.strip().lower()

        if not normalized_query:
            return []

        matches = []

        for occupation in occupation_records:
            secondary_text = occupation.get(
                "category",
                occupation.get("code", ""),
            )
            searchable_text = (
                f"{occupation['title']} {secondary_text}"
            ).lower()

            if normalized_query in searchable_text:
                matches.append(occupation)

        # Titles beginning with the search text appear first.
        matches.sort(
            key=lambda occupation: (
                not occupation["title"]
                .lower()
                .startswith(normalized_query),
                occupation["title"],
            )
        )

        return matches[:MAX_RESULTS]

    def hide_results():
        nonlocal results_open

        results_open = False
        results_container.opacity = 0
        results_container.height = 0

    def calculate_results_height(result_count: int) -> float:
        if result_count <= 0:
            return RESULT_HEIGHT + RESULTS_PADDING

        divider_count = max(0, result_count - 1)

        return (
            result_count * RESULT_HEIGHT
            + divider_count
            + RESULTS_PADDING
        )

    def create_result_click_handler(
        occupation: dict[str, str],
    ):
        async def select_result(e):
            search_field.value = occupation["title"]
            clear_button.visible = True

            hide_results()

            selected_result_text.value = (
                f"Selected: {occupation['title']}"
                if show_selection_text
                else ""
            )

            if collapse_on_select:
                collapse_search()
            else:
                page.update()
                await search_field.focus()

            if on_select is not None:
                await on_select(occupation)

        return select_result

    def create_result_control(
        occupation: dict[str, str],
    ) -> ft.Container:
        return ft.Container(
            height=RESULT_HEIGHT,
            padding=0,
            border_radius=0,
            ink=True,
            ink_color=ft.Colors.WHITE_10,
            on_click=create_result_click_handler(occupation),
            content=ft.Container(
                padding=ft.Padding.symmetric(
                    horizontal=16,
                    vertical=8,
                ),
                content=ft.Row(
                    controls=[
                        # Every result now has a search icon.
                        (
                            search_result_icon_factory()
                            if search_result_icon_factory is not None
                            else ft.Icon(
                                icon=ft.Icons.SEARCH_ROUNDED,
                                size=21,
                                color=ft.Colors.WHITE_70,
                            )
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    value=occupation["title"],
                                    size=15,
                                    color=ft.Colors.WHITE,
                                    weight=ft.FontWeight.W_500,
                                    max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            spacing=2,
                            tight=True,
                            expand=True,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ),
        )

    def show_results(
        matches: list[dict[str, str]],
        query: str,
        error_message: str | None = None,
    ):
        nonlocal results_open

        results_column.controls.clear()

        if matches:
            for index, occupation in enumerate(matches):
                results_column.controls.append(
                    create_result_control(occupation)
                )

                if index < len(matches) - 1:
                    results_column.controls.append(
                        ft.Divider(
                            height=1,
                            thickness=1,
                            color=ft.Colors.WHITE_10,

                        )
                    )

            result_count = len(matches)

        else:
            results_column.controls.append(
                ft.Container(
                    height=RESULT_HEIGHT,
                    padding=ft.Padding.symmetric(horizontal=16),
                    alignment=ft.Alignment.CENTER_LEFT,
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                icon=ft.Icons.SEARCH_OFF_ROUNDED,
                                size=21,
                                color=ft.Colors.WHITE_54,
                            ),
                            ft.Text(
                                value=(
                                    error_message
                                    or (
                                        "No results found for "
                                        f'"{query}"'
                                    )
                                ),
                                size=14,
                                color=ft.Colors.WHITE_54,
                                expand=True,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=12,
                    ),
                )
            )

            result_count = 0

        results_container.height = calculate_results_height(
            result_count
        )
        results_container.opacity = 1
        results_open = True

    async def find_results(
        query: str,
    ) -> list[dict[str, str]]:
        if search_provider is None:
            return filter_results(query)

        matches = await search_provider(query)
        return list(matches)[:MAX_RESULTS]

    async def refresh_results(
        query: str,
        revision: int,
        *,
        delay: float = 0,
    ):
        if delay:
            await asyncio.sleep(delay)

        if revision != search_revision:
            return

        try:
            matches = await find_results(query)
        except Exception:
            if revision != search_revision:
                return
            show_results(
                [],
                query,
                error_message=(
                    "Occupation search is unavailable. "
                    "Please try again."
                ),
            )
        else:
            if revision != search_revision:
                return
            show_results(matches, query)

        page.update()

    async def expand_search():
        nonlocal search_expanded

        search_expanded = True

        search_field.visible = True
        search_container.width = EXPANDED_WIDTH
        search_button.bgcolor = (
            expanded_search_button_bgcolor
            if expanded_search_button_bgcolor is not None
            else search_button_bgcolor
        )
        search_button.tooltip = "Search"

        page.update()
        await search_field.focus()

    def collapse_search():
        nonlocal search_expanded, search_revision

        search_expanded = False
        search_revision += 1

        search_field.value = ""
        search_field.visible = False

        clear_button.visible = False
        search_container.width = collapsed_width
        search_button.bgcolor = search_button_bgcolor
        search_button.tooltip = "Open search"

        hide_results()

        selected_result_text.value = ""

        page.update()

    async def search_button_clicked(e):
        nonlocal search_revision

        if not search_expanded:
            await expand_search()
            return

        query = search_field.value.strip()

        if not query:
            collapse_search()
            return

        search_revision += 1
        await refresh_results(query, search_revision)

    async def search_text_changed(e):
        nonlocal search_revision

        query = search_field.value.strip()
        search_revision += 1
        revision = search_revision

        # The clear button only appears when text has been entered.
        clear_button.visible = bool(query)
        selected_result_text.value = ""

        if query:
            if search_provider is None:
                show_results(filter_results(query), query)
                page.update()
            else:
                hide_results()
                page.update()
                await refresh_results(
                    query,
                    revision,
                    delay=0.25,
                )
        else:
            hide_results()
            page.update()

    async def clear_search(e):
        nonlocal search_revision

        search_revision += 1
        search_field.value = ""
        clear_button.visible = False
        selected_result_text.value = ""

        hide_results()

        page.update()
        await search_field.focus()

    async def submit_search(e):
        nonlocal search_revision

        query = search_field.value.strip()
        search_revision += 1
        revision = search_revision

        if not query:
            hide_results()
            selected_result_text.value = ""
            page.update()
        else:
            await refresh_results(query, revision)

    search_button = ft.IconButton(
        icon=(
            search_button_icon
            if search_button_icon is not None
            else ft.Icons.SEARCH_ROUNDED
        ),
        icon_color=ft.Colors.WHITE,
        icon_size=25,
        width=search_button_size,
        height=search_button_size,
        padding=0,
        alignment=ft.Alignment.CENTER,
        tooltip="Open search",
        bgcolor=search_button_bgcolor,
        hover_color=ft.Colors.WHITE_10,
        on_click=search_button_clicked,
    )

    search_field = ft.TextField(
        expand=True,
        height=search_height,
        visible=False,
        hint_text="Search occupations...",
        border=ft.InputBorder.NONE,
        text_size=15,
        color=ft.Colors.WHITE,
        cursor_color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(
            size=15,
            color=ft.Colors.WHITE_54,
        ),
        content_padding=ft.Padding.only(
            left=2,
            right=4,
            top=0,
            bottom=0,
        ),
        on_change=search_text_changed,
        on_submit=submit_search,
    )

    clear_button = ft.IconButton(
        icon=(
            clear_button_icon
            if clear_button_icon is not None
            else ft.Icons.CLOSE_ROUNDED
        ),
        icon_color=ft.Colors.WHITE_70,
        icon_size=21,
        width=48,
        height=search_height,
        padding=0,
        alignment=ft.Alignment.CENTER,
        tooltip="Clear search",
        visible=False,
        hover_color=ft.Colors.WHITE_10,
        on_click=clear_search,
    )

    search_container = ft.Container(
        width=collapsed_width,
        height=search_height,
        bgcolor="#202124",
        border_radius=search_height / 2,
        padding=0,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        animate=ft.Animation(
            duration=300,
            curve=ft.AnimationCurve.EASE_IN_OUT,
        ),
        content=ft.Row(
            controls=[
                # Fixed dimensions center the icon in the circle.
                # When expanded, the input appears to its right.
                search_button,
                search_field,
                clear_button,
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    search_controls = [search_container, results_container]
    if show_selection_text:
        search_controls.append(selected_result_text)

    search_control = ft.Column(
        controls=search_controls,
        width=EXPANDED_WIDTH,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    if mount:
        page.add(search_control)

    return search_control


if __name__ == "__main__":
    ft.run(main)

