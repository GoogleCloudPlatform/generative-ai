import re
from typing import Optional, Callable

def normalize(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[\s\.,;:!\?\-_/\\]+$", "", s)
    return s

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

def judge_validity(pred: str, gold: str, unknown_ok: bool, eq_fn: Optional[Callable[[str, str], bool]] = None) -> bool:
    s = normalize(pred)
    if unknown_ok:
        return s == "idk"
    if eq_fn is None:
        eq_fn = str_or_num_equal
    return bool(eq_fn(pred, gold))
