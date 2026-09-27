import flet as ft
import flet_charts as fch


PAGE_BG = "#000000"
CARD_BG = "#050505"
CARD_BORDER = "#292929"
DIVIDER = "#252525"
TEXT = "#E6E6E6"
MUTED = "#858585"
GRID = "#242424"
GRID_STRONG = "#343434"
ORANGE = "#FF861C"


class SkillsMapCard(ft.Container):
    def __init__(
        self,
        skill_data: fch.RadarDataSet,
        maximum_data: fch.RadarDataSet,
        radar_chart: fch.RadarChart,
        message_host: ft.Container,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._skill_data = skill_data
        self._maximum_data = maximum_data
        self._radar_chart = radar_chart
        self._message_host = message_host
        self.skills: list[dict[str, str]] = []

    def set_skills(self, skills: list[dict[str, str]]):
        self.skills = list(skills[:6])
        if not self.skills:
            self.set_message(
                "No O*NET skills are available for this occupation."
            )
            return

        self._skill_data.entries = [
            fch.RadarDataSetEntry(100)
            for _ in self.skills
        ]
        self._maximum_data.entries = [
            fch.RadarDataSetEntry(100)
            for _ in self.skills
        ]
        self._radar_chart.titles = [
            fch.RadarChartTitle(
                text=f"{index}. {skill['name']}",
                angle=360,
            )
            for index, skill in enumerate(self.skills, start=1)
        ]
        self._radar_chart.visible = True
        self._message_host.visible = False

    def set_message(self, message: str):
        self._message_host.content.value = message
        self._message_host.visible = True
        self._radar_chart.visible = False


def main(page: ft.Page):
    page.title = "Skills Map"
    page.bgcolor = PAGE_BG
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    skill_data = fch.RadarDataSet(
        fill_color=ft.Colors.with_opacity(0.30, ORANGE),
        border_color=ORANGE,
        border_width=3,
        entry_radius=4,
        entries=[],
    )
    maximum_data = fch.RadarDataSet(
        fill_color=ft.Colors.TRANSPARENT,
        border_color=ft.Colors.TRANSPARENT,
        border_width=0,
        entry_radius=0,
        entries=[],
    )
    radar_chart = fch.RadarChart(
        expand=True,
        titles=[],
        radar_shape=fch.RadarShape.POLYGON,
        tick_count=4,
        interactive=False,
        center_min_value=False,
        radar_bgcolor=ft.Colors.TRANSPARENT,
        title_text_style=ft.TextStyle(
            size=11,
            color=MUTED,
            weight=ft.FontWeight.W_500,
        ),
        title_position_percentage_offset=0.30,
        ticks_text_style=ft.TextStyle(
            size=7,
            color="#353535",
        ),
        grid_border_side=ft.BorderSide(
            width=1,
            color=GRID_STRONG,
        ),
        tick_border_side=ft.BorderSide(
            width=1,
            color=GRID,
        ),
        radar_border_side=ft.BorderSide(
            width=1,
            color="#3A3A3A",
        ),
        data_sets=[skill_data, maximum_data],
        visible=False,
    )
    message_host = ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Text(
            "Select an occupation to load its top O*NET skills.",
            size=12,
            color=MUTED,
            text_align=ft.TextAlign.CENTER,
        ),
    )

    skills_card = SkillsMapCard(
        skill_data=skill_data,
        maximum_data=maximum_data,
        radar_chart=radar_chart,
        message_host=message_host,
        width=400,
        height=470,
        bgcolor=CARD_BG,
        border=ft.Border.all(1, CARD_BORDER),
        border_radius=12,
        padding=ft.Padding(
            left=22,
            right=22,
            top=24,
            bottom=18,
        ),
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Skills Map",
                        size=18,
                        color=TEXT,
                        weight=ft.FontWeight.BOLD,
                    ),
                ),
                ft.Container(
                    height=1,
                    margin=ft.Margin.only(top=13, bottom=8),
                    bgcolor=DIVIDER,
                ),
                ft.Stack(
                    expand=True,
                    controls=[
                        radar_chart,
                        message_host,
                    ],
                ),
            ],
        ),
    )

    page.add(ft.SafeArea(content=skills_card))


if __name__ == "__main__":
    ft.run(main)
