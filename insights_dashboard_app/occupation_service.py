import asyncio

from oews_service import OewsWageService, soc_code_from_onet
from onet_service import OnetService


class OccupationService:
    def __init__(
        self,
        onet_service: OnetService,
        oews_service: OewsWageService,
    ):
        self._onet_service = onet_service
        self._oews_service = oews_service

    async def get_occupation(
        self,
        onet_code: str,
        title: str,
    ) -> dict:
        code = onet_code.strip()
        occupation_title = title.strip()
        if not code or not occupation_title:
            raise ValueError(
                "An O*NET-SOC code and occupation title are required."
            )

        skills, median_wages = await asyncio.gather(
            self._onet_service.get_skills(code, limit=6),
            asyncio.to_thread(
                self._oews_service.get_wage_history,
                code,
            ),
        )

        return {
            "onet_code": code,
            "soc_code": soc_code_from_onet(code),
            "title": occupation_title,
            "skills": skills[:6],
            "median_wages": median_wages,
        }
