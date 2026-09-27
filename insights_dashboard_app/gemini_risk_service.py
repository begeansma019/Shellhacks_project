import asyncio
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import create_client, run_risk_prediction


class GeminiRiskServiceError(RuntimeError):
    pass


class GeminiRiskService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        resolved_api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY", "").strip()
        )

        self._model = (
            model
            or os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ).strip()
        )

        self._client = (
            create_client(resolved_api_key)
            if resolved_api_key
            else None
        )

        self._cache: dict[str, dict] = {}
        self._inflight: dict[str, asyncio.Task] = {}

    async def analyze_occupation(
        self,
        title: str,
        *,
        context: str = "",
    ) -> dict:
        if self._client is None:
            raise GeminiRiskServiceError(
                "Missing GEMINI_API_KEY."
            )

        key = title.strip().casefold()

        if key in self._cache:
            return self._cache[key]

        existing = self._inflight.get(key)

        if existing is not None:
            try:
                return await asyncio.shield(existing)
            except Exception as error:
                raise GeminiRiskServiceError(
                    str(error)
                ) from error

        task = asyncio.create_task(
            run_risk_prediction(
                self._client,
                self._model,
                title,
                context,
            )
        )

        self._inflight[key] = task

        try:
            result = await asyncio.shield(task)

            if result.get("source") == "gemini":
                self._cache[key] = result

            return result

        except Exception as error:
            raise GeminiRiskServiceError(
                str(error)
            ) from error

        finally:
            if self._inflight.get(key) is task:
                self._inflight.pop(key, None)