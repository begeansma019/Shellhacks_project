import asyncio
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ONET_BASE_URL = "https://api-v2.onetcenter.org"
ONET_API_KEY_ENV = "ONET_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 10.0


class OnetServiceError(RuntimeError):
    """A user-safe O*NET request or response failure."""


class OnetService:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = ONET_BASE_URL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._api_key = api_key or os.getenv(ONET_API_KEY_ENV, "")
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def search_occupations(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, str]]:
        keyword = query.strip()
        if not keyword:
            return []

        payload = await asyncio.to_thread(
            self._get_json,
            "/online/search",
            {
                "keyword": keyword,
                "start": 1,
                "end": max(1, limit),
            },
        )
        occupations = payload.get("occupation", [])
        if not isinstance(occupations, list):
            raise OnetServiceError(
                "O*NET returned an invalid occupation search response."
            )

        results = []
        for occupation in occupations:
            if not isinstance(occupation, dict):
                continue
            code = occupation.get("code")
            title = occupation.get("title")
            if isinstance(code, str) and isinstance(title, str):
                results.append({"code": code, "title": title})

        return results[:limit]

    async def get_skills(
        self,
        onet_code: str,
        *,
        limit: int = 6,
    ) -> list[dict[str, object]]:
        code = onet_code.strip()
        if not code:
            raise ValueError("An O*NET-SOC code is required.")

        requested_limit = min(max(1, limit), 6)
        encoded_code = quote(code, safe="-.")
        payload = await asyncio.to_thread(
            self._get_json,
            (
                f"/online/occupations/{encoded_code}"
                "/details/skills"
            ),
            {
                "start": 1,
                "end": requested_limit,
                "sort": "importance",
            },
        )
        elements = payload.get("element", [])
        if not isinstance(elements, list):
            raise OnetServiceError(
                "O*NET returned an invalid skills response."
            )

        skills = []
        for element in elements:
            if not isinstance(element, dict):
                continue
            skill_id = element.get("id")
            name = element.get("name")
            description = element.get("description")
            importance = element.get("importance")
            if all(
                isinstance(value, str)
                for value in (skill_id, name, description)
            ):
                try:
                    importance_value = float(importance)
                except (TypeError, ValueError):
                    importance_value = 0.0

                importance_value = max(
                    0.0,
                    min(100.0, importance_value),
                )
                skills.append(
                    {
                        "id": skill_id,
                        "name": name,
                        "description": description,
                        "importance": importance_value,
                    }
                )

        return skills[:requested_limit]

    def _get_json(
        self,
        path: str,
        query: dict[str, object] | None = None,
    ) -> dict:
        if not self._api_key:
            raise OnetServiceError(
                f"Set {ONET_API_KEY_ENV} before using O*NET search."
            )

        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-API-Key": self._api_key,
            },
            method="GET",
        )

        for attempt in range(2):
            try:
                with urlopen(
                    request,
                    timeout=self._timeout_seconds,
                ) as response:
                    payload = json.load(response)
                if not isinstance(payload, dict):
                    raise OnetServiceError(
                        "O*NET returned an invalid JSON response."
                    )
                return payload
            except HTTPError as error:
                if error.code == 429 and attempt == 0:
                    time.sleep(0.25)
                    continue
                message = self._http_error_message(error)
                raise OnetServiceError(message) from error
            except (URLError, TimeoutError) as error:
                raise OnetServiceError(
                    "O*NET is unavailable or timed out. Please try again."
                ) from error
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise OnetServiceError(
                    "O*NET returned an unreadable response."
                ) from error

        raise OnetServiceError(
            "O*NET is temporarily rate limited. Please try again."
        )

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        if error.code == 401 or error.code == 403:
            return "O*NET rejected the configured API key."
        if error.code == 404:
            return "The requested O*NET occupation was not found."
        if error.code == 429:
            return "O*NET is temporarily rate limited. Please try again."
        return (
            f"O*NET request failed with HTTP status {error.code}."
        )
