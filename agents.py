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
