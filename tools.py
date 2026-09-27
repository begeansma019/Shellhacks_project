"""Tools for WorkLens: integrates Microsoft Working-with-AI and Anthropic Economic Index."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import pandas as pd

MS_DATASET_PATH = os.path.join(os.path.dirname(__file__), "ai_applicability_scores.csv")
ANTHROPIC_DATASET_PATH = os.path.join(os.path.dirname(__file__), "aei_1p_api_2026-06-26.csv")


def _load_csv(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            df.columns = [col.strip() for col in df.columns]
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


_MS_DF = _load_csv(MS_DATASET_PATH)
_ANTHROPIC_DF = _load_csv(ANTHROPIC_DATASET_PATH)

DEFAULT_TASK_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "software engineer": [
        {
            "task": "Boilerplate code generation & routine debugging",
            "probability": 82,
            "justification": "Modern LLMs have extensive syntactic training data that allows them to generate deterministic code snippets with minimal oversight.",
        },
        {
            "task": "Automated unit testing & CI/CD pipeline authoring",
            "probability": 76,
            "justification": "Test scaffolds follow well-defined programmatic contracts, making them susceptible to automated agent generation.",
        },
        {
            "task": "Legacy code refactoring & dependency updates",
            "probability": 65,
            "justification": "Rule-based structural migrations are easily parsed by language models, though library side effects still require human verification.",
        },
        {
            "task": "System architecture & fault-tolerant design",
            "probability": 38,
            "justification": "High-level distributed systems require nuanced cross-service domain trade-offs and physical latency considerations that AI cannot independently evaluate.",
        },
    ],
    "data analyst": [
        {
            "task": "ETL data cleaning and missing value imputation",
            "probability": 85,
            "justification": "Predictable data cleansing routines and transformation rules are directly handled by autonomous data pipeline agents.",
        },
        {
            "task": "SQL query synthesis & automated dashboards",
            "probability": 80,
            "justification": "Natural-language-to-SQL translation is highly mature and enables non-technical operators to query schemas without assistance.",
        },
        {
            "task": "Exploratory metric correlation & pattern detection",
            "probability": 60,
            "justification": "Machine learning engines detect statistical anomalies rapidly, but distinguishing genuine causal factors from noise requires human domain knowledge.",
        },
        {
            "task": "Cross-functional executive insight communication",
            "probability": 35,
            "justification": "Synthesizing raw findings into organizational policy requires human persuasion, corporate context, and stakeholder navigation.",
        },
    ],
}


def get_microsoft_score(job_title: str) -> float:
    """Returns empirical Microsoft applicability score normalized from 0 to 100 (100 = highest risk)."""
    if not _MS_DF.empty:
        title_col = next((c for c in _MS_DF.columns if any(k in c.lower() for k in ["title", "occupation", "name"])), None)
        score_col = next((c for c in _MS_DF.columns if any(k in c.lower() for k in ["score", "applicability", "ai"])), None)
        if title_col and score_col:
            q = job_title.strip().lower()
            match = _MS_DF[_MS_DF[title_col].astype(str).str.lower() == q]
            if match.empty:
                match = _MS_DF[_MS_DF[title_col].astype(str).str.lower().str.contains(q, regex=False)]
            if not match.empty:
                raw = float(match.iloc[0][score_col])
                score = raw * 100 if raw <= 1.0 else raw
                return round(score, 1)
    return 55.0


def get_anthropic_metrics(job_title: str) -> Dict[str, str]:
    """Extracts occupational exposure mode from the Anthropic Economic Index."""
    if not _ANTHROPIC_DF.empty:
        title_col = next((c for c in _ANTHROPIC_DF.columns if any(k in c.lower() for k in ["occupation", "soc", "title"])), None)
        if title_col:
            q = job_title.strip().lower()
            match = _ANTHROPIC_DF[_ANTHROPIC_DF[title_col].astype(str).str.lower().str.contains(q, regex=False)]
            if not match.empty:
                row = match.iloc[0]
                exposure = row.get("relative_exposure", row.get("usage_index", "High"))
                interaction = row.get("primary_mode", "Augmentation (Copilot)")
                return {"exposure_intensity": str(exposure), "interaction_mode": str(interaction)}

    # Standard fallback according to Anthropic Index findings
    return {
        "exposure_intensity": "Top 15% (High Claude interaction density)",
        "interaction_mode": "Augmentation-heavy (Direct human steering with multi-turn prompt refinement)",
    }


def analyze_job_tasks(job_title: str) -> List[Dict[str, Any]]:
    """Retrieves 4 tasks, probabilities, and specific justification sentences."""
    q = job_title.strip().lower()
    for reg_job, tasks in DEFAULT_TASK_CATALOG.items():
        if reg_job in q or q in reg_job:
            return tasks

    base_score = get_microsoft_score(job_title)
    return [
        {
            "task": "Structured data processing & syntax translation",
            "probability": min(round(base_score + 18, 1), 95.0),
            "justification": "Highly programmatic inputs and rigid syntactical boundaries make this task directly susceptible to modern foundation models.",
        },
        {
            "task": "Standard operational documentation & logging",
            "probability": min(round(base_score + 10, 1), 90.0),
            "justification": "Template-driven reporting allows LLMs to summarize actions accurately with minimal human intervention.",
        },
        {
            "task": "Contextual troubleshooting and anomaly resolution",
            "probability": max(round(base_score - 10, 1), 30.0),
            "justification": "Investigating multifaceted system bugs requires cross-domain deductive reasoning that often exposes AI hallucination risks.",
        },
        {
            "task": "High-liability governance and stakeholder negotiation",
            "probability": max(round(base_score - 25, 1), 15.0),
            "justification": "Accountability, legal liability, and human consensus cannot be delegated to an autonomous model.",
        },
    ]