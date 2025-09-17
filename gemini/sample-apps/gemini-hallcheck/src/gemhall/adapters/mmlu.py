import csv
import os
import random
from collections.abc import Iterable

from datasets import concatenate_datasets, load_dataset

SUBJECTS_ALL = [
    "abstract_algebra",
    "anatomy",
    "astronomy",
    "business_ethics",
    "clinical_knowledge",
    "college_biology",
    "college_chemistry",
    "college_computer_science",
    "college_mathematics",
    "college_medicine",
    "college_physics",
    "computer_security",
    "conceptual_physics",
    "econometrics",
    "electrical_engineering",
    "elementary_mathematics",
    "formal_logic",
    "global_facts",
    "high_school_biology",
    "high_school_chemistry",
    "high_school_computer_science",
    "high_school_european_history",
    "high_school_geography",
    "high_school_government_and_politics",
    "high_school_macroeconomics",
    "high_school_mathematics",
    "high_school_microeconomics",
    "high_school_physics",
    "high_school_psychology",
    "high_school_statistics",
    "high_school_us_history",
    "high_school_world_history",
    "human_aging",
    "human_sexuality",
    "international_law",
    "jurisprudence",
    "logical_fallacies",
    "machine_learning",
    "management",
    "marketing",
    "medical_genetics",
    "miscellaneous",
    "moral_disputes",
    "moral_scenarios",
    "nutrition",
    "philosophy",
    "prehistory",
    "professional_accounting",
    "professional_law",
    "professional_medicine",
    "professional_psychology",
    "public_relations",
    "security_studies",
    "sociology",
    "us_foreign_policy",
    "virology",
    "world_religions",
]

LETTERS = "ABCD"


def _format_item(q: str, choices: list[str]) -> str:
    options = "\n".join(f"{LETTERS[i]}. {c}" for i, c in enumerate(choices[:4]))
    return f"{q}\n\nOptions:\n{options}\n\nReply with A, B, C, or D."


def _gold_letter(answer_field) -> str:
    if isinstance(answer_field, int):
        return LETTERS[answer_field]
    s = str(answer_field).strip().upper()
    if s in set(LETTERS):
        return s
    try:
        return LETTERS[int(s)]
    except (ValueError, IndexError):
        raise ValueError(f"Invalid answer format: {answer_field}")


def _answer_index(answer_field) -> int:
    if isinstance(answer_field, int):
        return int(answer_field)
    s = str(answer_field).strip().upper()
    if s in set(LETTERS):
        return LETTERS.index(s)
    return int(s)


def export_temp_csv(
    out_csv: str,
    split: str = "test",
    subjects: Iterable[str] | None = None,
    limit: int | None = None,
    seed: int = 1234,
    idk_frac: float = 0.0,
) -> str:
    """Loads cais/mmlu from Hugging Face, filters subjects/split, optionally samples `limit` items,
    optionally converts a fraction into IDK-only, and writes a CSV for the evaluator.
    """
    wanted_subjects = list(subjects) if subjects else SUBJECTS_ALL

    # Try unified "all" config first
    table = None
    try:
        ds = load_dataset("cais/mmlu", name="all")
        if split not in ds:
            raise ValueError(
                f"Split '{split}' not found in cais/mmlu. Available: {list(ds.keys())}"
            )
        table = ds[split]
        if wanted_subjects != ["all"]:
            allowed = set(wanted_subjects)
            if "subject" in table.column_names:
                table = table.filter(lambda ex: ex.get("subject", "") in allowed)
            else:
                raise RuntimeError("Unified config missing 'subject' column")
    except Exception:
        # Fallback: concat selected subjects
        subjects_to_load = (
            SUBJECTS_ALL if wanted_subjects == ["all"] else wanted_subjects
        )
        parts = []
        for subj in subjects_to_load:
            d = load_dataset("cais/mmlu", name=subj)
            if split not in d:
                continue
            ds_split = d[split]
            if "subject" not in ds_split.column_names:
                ds_split = ds_split.map(lambda ex: {"subject": subj})
            parts.append(ds_split)
        if not parts:
            raise ValueError(
                f"No data found for split '{split}' and subjects {subjects_to_load}"
            )
        table = concatenate_datasets(parts)

    # Random sampling after subject filtering
    if limit is not None and limit < len(table):
        rnd = random.Random(seed)
        idxs = rnd.sample(range(len(table)), limit)
        table = table.select(idxs)

    # Decide which rows become IDK-only
    rnd = random.Random(seed)
    n = len(table)
    k = round(max(0.0, min(1.0, idk_frac)) * n)
    idk_idxs = set(rnd.sample(range(n), k)) if k > 0 else set()

    rows: list[dict[str, str]] = []
    for i, ex in enumerate(table):
        q = ex["question"]
        choices = list(ex["choices"])
        if not isinstance(choices, list) or len(choices) < 4:
            continue
        subj = ex.get("subject", "mmlu")
        if i in idk_idxs:
            gi = _answer_index(ex["answer"])  # correct option index 0..3
            distractors = [j for j in range(4) if j != gi]
            repl = rnd.choice(distractors)
            choices[gi] = choices[
                repl
            ]  # duplicate a distractor -> no true option remains
            question = _format_item(q, choices[:4])
            rows.append(
                {
                    "id": f"{subj}:{i}",
                    "question": question,
                    "gold": "",
                    "unknown_ok": 1,
                    "category": f"{subj}|unanswerable",
                }
            )
        else:
            ans = _gold_letter(ex["answer"])
            question = _format_item(q, choices[:4])
            rows.append(
                {
                    "id": f"{subj}:{i}",
                    "question": question,
                    "gold": ans,
                    "unknown_ok": 0,
                    "category": subj,
                }
            )

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["id", "question", "gold", "unknown_ok", "category"]
        )
        w.writeheader()
        w.writerows(rows)
    return out_csv
