import json
import os
import sys
from google import genai
from google.genai import errors
from tools import analyze_job_tasks, get_microsoft_score


def create_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _generate_dataset_report(job_title: str) -> str:
    """Build the fallback report from Microsoft applicability data."""
    ms_score = get_microsoft_score(job_title)
    tasks = analyze_job_tasks(job_title)

    task_bullets = "\n".join([
        f"- **{t['task']}** — **{t['probability']}% Automation Probability**\n"
        f"  *Justification*: {t['justification']}"
        for t in tasks[:4]
    ])

    return (
        f"## 1. EMPIRICAL BENCHMARK SCORE\n"
        f"- **Microsoft AI Applicability Score**: {ms_score}/100 — "
        f"Empirical measure of how applicable generative AI is to the occupation's work activities.\n\n"
        f"## 2. CORE TASK BREAKDOWN & JUSTIFICATIONS\n"
        f"{task_bullets}"
    )


def run_full_pipeline(client: genai.Client, model: str, job_title: str, context: str = "") -> dict:
    clean_model = model.replace("models/", "").strip()
    ms_score = get_microsoft_score(job_title)
    tasks = analyze_job_tasks(job_title)

    task_context_block = "\n".join([
        f"- Task: {t['task']} | Probability: {t['probability']}%\n  Context: {t['justification']}"
        for t in tasks[:4]
    ])

    system_instruction = (
        "You are WorkLens, an occupational workforce AI intelligence engine. "
        "Strictly structure your response using ONLY the following sections and Markdown format:\n\n"
        "## 1. EMPIRICAL BENCHMARK SCORE\n"
        "- Microsoft AI Applicability Score: [State score as X/100] — [1 sentence explaining what the empirical applicability score indicates]\n\n"
        "## 2. CORE TASK BREAKDOWN & JUSTIFICATIONS\n"
        "Present the 4 tasks in bullet points. For each task provide:\n"
        "- **[Task Name]** — **[X]% Automation Probability**\n"
        "  *Justification*: [1 concise sentence clearly explaining why it receives this percentage based on AI capability limitations or strengths.]"
    )

    user_prompt = (
        f"Occupation: {job_title}\n"
        f"Microsoft AI Applicability Score: {ms_score}/100\n"
        f"Pre-analyzed Tasks:\n{task_context_block}\n"
        f"Extra Context: {context.strip() or 'None'}"
    )

    try:
        response = client.chats.create(
            model=clean_model,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
        result = response.send_message(user_prompt)
        return {"full_report": result.text.strip()}

    except Exception as e:
        err = str(e)
        if any(code in err for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded", "high demand"]):
            print("\n[Notice] API limit/unavailable (503/429). Serving empirical Microsoft dataset analysis...\n")
            return {"full_report": _generate_dataset_report(job_title)}
        raise e


def run_risk_prediction(
    client: genai.Client,
    model: str,
    job_title: str,
    context: str = "",
) -> dict:
    ms_score = get_microsoft_score(job_title)
    tasks = analyze_job_tasks(job_title)

    def clamp_score(value) -> int:
        return int(round(max(0, min(100, float(value)))))

    def normalize_tasks(predicted_tasks) -> list[dict]:
        normalized_tasks = []

        if isinstance(predicted_tasks, list):
            for task in predicted_tasks[:4]:
                if not isinstance(task, dict):
                    continue

                task_name = str(task.get("task", "")).strip()
                justification = str(
                    task.get("justification", "")
                ).strip()
                if not task_name:
                    continue

                try:
                    probability = clamp_score(task["probability"])
                except (KeyError, TypeError, ValueError):
                    continue

                normalized_tasks.append(
                    {
                        "task": task_name,
                        "probability": probability,
                        "justification": justification,
                    }
                )

        for task in tasks:
            if len(normalized_tasks) == 4:
                break
            normalized_tasks.append(
                {
                    "task": str(task["task"]).strip(),
                    "probability": clamp_score(task["probability"]),
                    "justification": str(
                        task["justification"]
                    ).strip(),
                }
            )

        return normalized_tasks[:4]

    def microsoft_fallback() -> dict:
        return {
            "risk_score": clamp_score(round(ms_score)),
            "summary": (
                "Gemini was temporarily unavailable; Microsoft "
                "applicability data is being shown."
            ),
            "tasks": normalize_tasks([]),
            "source": "microsoft_fallback",
        }

    response_schema = {
        "type": "object",
        "properties": {
            "risk_score": {"type": "integer"},
            "summary": {"type": "string"},
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "probability": {"type": "integer"},
                        "justification": {"type": "string"},
                    },
                    "required": [
                        "task",
                        "probability",
                        "justification",
                    ],
                },
            },
        },
        "required": ["risk_score", "summary", "tasks"],
    }

    instruction = (
        "You are WorkLens's occupational AI-risk analyst. Use the "
        "selected O*NET occupation, Microsoft AI Applicability Score, "
        "supporting task context, and optional O*NET context to produce "
        "the prediction. The Microsoft score is empirical evidence of "
        "generative-AI applicability, not automatically the final risk "
        "score. Return one overall integer risk_score from 0 to 100 and "
        "exactly four occupation-specific tasks. Each task must include "
        "an integer AI-risk probability from 0 to 100 and a concise "
        "justification. Use no other dataset. Do not output Markdown. "
        "Return structured JSON only."
    )
    prompt = (
        f"Occupation: {job_title}\n"
        f"Microsoft AI Applicability Score: {ms_score} / 100\n\n"
        f"Supporting task context:\n"
        f"{json.dumps(tasks[:4], ensure_ascii=False)}\n\n"
        f"O*NET context:\n{context.strip() or 'None'}"
    )

    try:
        response = client.models.generate_content(
            model=model.replace("models/", "").strip(),
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2,
            ),
        )
        prediction = json.loads(response.text)
        return {
            "risk_score": clamp_score(prediction["risk_score"]),
            "summary": str(prediction.get("summary", "")).strip(),
            "tasks": normalize_tasks(prediction["tasks"]),
            "source": "gemini",
        }
    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        AttributeError,
    ):
        return microsoft_fallback()
    except Exception as error:
        message = str(error)
        temporary_errors = (
            "503",
            "429",
            "UNAVAILABLE",
            "RESOURCE_EXHAUSTED",
            "overloaded",
            "high demand",
        )
        if any(code in message for code in temporary_errors):
            return microsoft_fallback()
        raise
