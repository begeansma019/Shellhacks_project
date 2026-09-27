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


async def run_risk_prediction(
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
        fallback_tasks = normalize_tasks([])
        fallback_share = clamp_score(
            sum(
                task["probability"]
                for task in fallback_tasks
            )
            / len(fallback_tasks)
        )
        return {
            "risk_score": clamp_score(round(ms_score)),
            "realizable_automation_share": fallback_share,
            "tasks": fallback_tasks,
            "source": "microsoft_fallback",
        }

    response_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "risk_score": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "realizable_automation_share": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
            },
            "tasks": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "task": {"type": "string"},
                        "probability": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                        },
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
        "required": [
            "risk_score",
            "realizable_automation_share",
            "tasks",
        ],
    }

    instruction = (
        "You are WorkLens, an occupational AI-risk analyst. "
        "Use the occupation, Microsoft AI Applicability Score, "
        "and seed task evidence to estimate occupational AI risk. "
        "The Microsoft score is evidence, not the final risk score. "
        "Also estimate realizable_automation_share from 0-100: the "
        "realistic share of annual occupational work effort that "
        "current AI could automate under human oversight. This is "
        "distinct from risk_score and should reflect task feasibility, "
        "workflow constraints, and remaining human work. Do not "
        "interpret a 70 risk score as 70% labor replacement. "
        "Return exactly four occupation-specific tasks. "
        "Keep task names concise and each justification to one short "
        "sentence of no more than about 18 words. "
        "Use no other dataset. Return only the required JSON."
    )
    prompt = (
        f"Occupation: {job_title}\n"
        f"Microsoft applicability: {ms_score}/100\n"
        f"Seed tasks: {json.dumps(tasks[:4], ensure_ascii=False)}"
    )
    if context.strip():
        prompt += f"\nContext: {context.strip()}"

    try:
        response = await client.aio.models.generate_content(
            model=model.replace("models/", "").strip(),
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=instruction,
                response_mime_type="application/json",
                response_json_schema=response_schema,
                thinking_config=genai.types.ThinkingConfig(
                    thinking_level="low",
                ),
            ),
        )
        prediction = json.loads(response.text)
        return {
            "risk_score": clamp_score(prediction["risk_score"]),
            "realizable_automation_share": clamp_score(
                prediction["realizable_automation_share"]
            ),
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
