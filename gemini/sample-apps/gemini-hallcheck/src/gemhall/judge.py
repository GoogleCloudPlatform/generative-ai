import re
from collections.abc import Callable


def normalize(s: str | None) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return re.sub(r"[\s\.,;:!\?\-_/\\]+$", "", s)


def numbers_equal(a: str, b: str) -> bool:
    try:
        return float(a) == float(b)
    except Exception:
        return False


def str_or_num_equal(a: str, b: str) -> bool:
    A, B = normalize(a), normalize(b)
    if A == B:
        return True
    return numbers_equal(A, B)


def judge_validity(
    pred: str,
    gold: str,
    unknown_ok: bool,
    eq_fn: Callable[[str, str], bool] | None = None,
) -> bool:
    s = normalize(pred)
    if unknown_ok:
        return s == "idk"
    if eq_fn is None:
        eq_fn = str_or_num_equal
    return bool(eq_fn(pred, gold))
