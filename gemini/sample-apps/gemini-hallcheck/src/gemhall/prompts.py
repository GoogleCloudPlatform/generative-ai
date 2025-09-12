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
    t_disp = f"{t:.2f}".rstrip("0").rstrip(".")
    return (
        f"{question}\n\n"
        f"Answer only if you are > {t_disp} confident.\n"
        f"Scoring: correct = +1, incorrect = -{pen}, 'IDK' = 0.\n"
        f"If you are not > {t_disp} confident, reply EXACTLY 'IDK'.\n"
        "Output only the final answer (or 'IDK')."
    )


def is_idk(text: str | None) -> bool:
    if text is None:
        return True
    s = text.strip().lower()
    return s == "idk" or s in IDK_TOKENS
