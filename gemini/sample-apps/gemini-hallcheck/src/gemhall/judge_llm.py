from google import genai
from google.genai import types

LLM_JUDGE_MODEL = "gemini-2.5-flash-lite"

SYSTEM = (
    "You are a strict binary grader. Decide if the candidate answer is semantically "
    "equivalent to the gold answer for the user question. "
    "Output ONLY one token: 'YES' or 'NO'. "
    "Be strict about factual equivalence, units, and exactness when appropriate. "
    "If the candidate says 'IDK' and the gold is blank, treat as 'YES'."
)

PROMPT_TMPL = (
    "Question: {question}\n"
    "Gold answer: {gold}\n"
    "Candidate answer: {pred}\n"
    "Respond strictly with YES or NO."
)


def _postprocess(text: str | None) -> str:
    s = (text or "").strip().upper()
    if "YES" in s and "NO" not in s:
        return "YES"
    if "NO" in s and "YES" not in s:
        return "NO"
    return "YES" if s.startswith("Y") else "NO"


class LLMJudge:
    def __init__(
        self,
        model: str = LLM_JUDGE_MODEL,
        temperature: float = 0.0,
        seed: int | None = 1234,
    ):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.seed = seed

    def judge(self, question: str, gold: str, pred: str, unknown_ok: bool) -> bool:
        if unknown_ok:
            return pred.strip().upper() == "IDK"
        contents = f"Question: {question}\nGold answer: {gold}\nCandidate answer: {pred}\nRespond strictly with YES or NO."
        cfg = types.GenerateContentConfig(
            temperature=self.temperature, seed=self.seed, max_output_tokens=4
        )
        resp = self.client.models.generate_content(
            model=self.model, contents=f"{SYSTEM}\n\n{contents}", config=cfg
        )
        return _postprocess(resp.text) == "YES"


class AsyncLLMJudge:
    def __init__(
        self,
        model: str = LLM_JUDGE_MODEL,
        temperature: float = 0.0,
        seed: int | None = 1234,
    ):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.seed = seed

    async def judge(
        self, question: str, gold: str, pred: str, unknown_ok: bool
    ) -> bool:
        if unknown_ok:
            return pred.strip().upper() == "IDK"
        contents = PROMPT_TMPL.format(question=question, gold=gold, pred=pred)
        cfg = types.GenerateContentConfig(
            temperature=self.temperature, seed=self.seed, max_output_tokens=4
        )
        resp = await self.client.aio.models.generate_content(
            model=self.model, contents=f"{SYSTEM}\n\n{contents}", config=cfg
        )
        return _postprocess(resp.text) == "YES"
