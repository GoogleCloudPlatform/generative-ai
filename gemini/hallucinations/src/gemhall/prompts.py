from typing import Optional

IDK_TOKENS = {
    "idk",
    "i don't know",
    "i do not know",
    "unknown",
    "cannot answer",
    "can't answer",
    "not sure",
}

def build_conf_prompt(question: str, t: float) -> str:
    pen = round(t / (1.0 - t), 3) if t < 1 else "infinite"
    return (
        f"{question}\n\n"
        "Answer only if you are > {t} confident.\n"
        "Scoring: correct = +1, incorrect = -{pen}, 'IDK' = 0.\n"
        "If you are not > {t} confident, reply EXACTLY 'IDK'.\n"
        "Output only the final answer (or 'IDK')."
    ).format(t=round(t, 2), pen=pen)

def is_idk(text: Optional[str]) -> bool:
    if text is None:
        return True
    s = text.strip().lower()
    return s == "idk" or s in IDK_TOKENS
