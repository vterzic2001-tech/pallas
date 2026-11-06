# coach_agent.py
import json
import random
import os
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=1.1,
    max_tokens=1200,
)

test_llm = ChatOpenAI(
    model="deepseek-chat",
    base_url="https://api.deepseek.com",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    temperature=0.2,
    max_tokens=600,
)

TASK_PROMPT = """You are PALLAS, an expert psychometric item writer for IQ-test reasoning tasks.
OUTPUT LANGUAGE: ENGLISH ONLY. Every field MUST be in English.
Return ONLY valid JSON. No markdown fences. No commentary before or after.

Category: {category}
Difficulty: {difficulty}/5

=== STEP 1: CHOOSE A PATTERN THAT MATCHES THE DIFFICULTY ===

STRICT DIFFICULTY LADDER (violating this is a failure):

sequences:
  1 = arithmetic only (+n) OR simple alternation (a,b,a,b)
  2 = geometric (xn) OR perfect squares (1,4,9,16)
  3 = affine (xn+c) OR interleaved two sequences
  4 = alternating operations (x2, +3, x2, +3) OR (xn then +n)
  5 = MULTIPLICATIVE / FIBONACCI-LIKE:
       a_n = a_(n-1) * a_(n-2) + c, or squaring with offset.
  6 = MASTER: Interleaved THREE sequences (e.g., +2, x2, -3 repeating).
  7 = MASTER: Alternating exponents or factorial growth.
  8 = MASTER: Two rules applied simultaneously (e.g., n^2 + n).
  9 = MASTER: Nested logic (e.g., previous term + sum of its digits).
  10 = GRANDMASTER: Highly abstract, multi-step operations.
       CRITICAL FOR LEVELS 8-10: You MUST provide at least 5 visible terms.
       DO NOT use "x^2 - 1" (that is a Level 5 rule).
       ABSOLUTELY FORBIDDEN at difficulty 5:
         * xn + c (like x2+1) — that is difficulty 3
         * xn only              — that is difficulty 2
         * +n only              — that is difficulty 1
       If you cannot construct a valid difficulty-5 sequence, LOWER the number count
       or use a DIFFERENT difficulty-5 pattern from the list above.

analogies:
  1 = category:member (apple:fruit) OR part:whole (wheel:car)
  2 = function:tool (knife:cut) OR cause:effect (rain:flood)
  3 = synonym OR antonym with nuance
  4 = degree/intensity (warm:hot :: cool:cold)
  5 = abstract relation (thesis:antithesis :: synthesis:?) — must require reasoning

matrices:
  1 = fill Latin square, single shape
  2 = shape Latin square, single fill
  3 = shape AND fill as simultaneous Latin squares
  4 = rotation across row (90° left) + fill alternation
  5 = multi-attribute change (e.g. number of sides increases AND fill cycles)

=== STEP 2: DERIVE BEFORE YOU WRITE ===

Before writing the final JSON, construct the sequence (or grid) term by term.
For sequences, your "derivation" field MUST look like:
  "a_1=2; a_2=a_1*1+1=3; a_3=a_2*2+1=7; a_4=a_3*3+1=22; a_5=a_4*4+1=89; a_6=a_5*5+1=446"
You MUST physically write out EVERY visible term.
If your derivation does not match the visible terms you plan to show, CHANGE THE RULE.
Do NOT state a rule you have not verified against every term.

For matrices, your derivation field must describe each row and column explicitly.

For analogies, your derivation field must state the precise relation in A:B, then verify C:D follows the same relation.

=== STEP 3: NUMBER LIMITS ===

- All numeric values must be < 100,000.
- For numeric options, at least 2 should be near-misses, 2 clearly wrong.
- Do NOT use "all of the above" / "none of the above".
- Do NOT prefix options with letters like "A ", "B ", "1. ". Just the text.

{previous_block}

=== OUTPUT SCHEMA (order matters — write derivation FIRST) ===
{
  "derivation": "step-by-step computation proving the rule matches every visible term",
  "rule": "one-sentence rule statement, DERIVED FROM derivation above (English)",
  "category": "{category}",
  "difficulty": {difficulty},
  "stem": "the question ending with '?'",
  "options": ["option 1", "option 2", "option 3", "option 4"],
  "correct_index": 0,
  "why_wrong": {
    "0": "why tempting but wrong (English)",
    "1": "why tempting but wrong",
    "2": "why tempting but wrong",
    "3": "why tempting but wrong"
  }
}

Set correct_index to the 0-3 index of the truly correct option.
In why_wrong, omit the key equal to correct_index.
"""

EXPLAIN_PROMPT = """You are PALLAS, a patient reasoning coach.
OUTPUT LANGUAGE: ENGLISH ONLY.

Item:
{stem}

Options:
0) {opt0}
1) {opt1}
2) {opt2}
3) {opt3}

Correct answer: index {correct_index} ({correct_text})
Rule: {rule}
Model's derivation: {derivation}

User answered: index {user_index} ({user_text})
Is user correct? {is_correct}

Write a short coaching response (max 120 words, plain English, no LaTeX, no asterisks, no bullets). Structure:
1. If correct: one-sentence affirmation, then state the rule clearly, showing ONE step from the derivation as proof.
2. If wrong: one sentence naming why {user_text} is tempting, then state the rule, then show why {correct_text} follows (using a step from the derivation).
3. End with: "Next time, look for ...".

Tone: warm, direct. Plain prose.
"""



VERIFY_PROMPT = """You are a strict math verifier. A task generator claims the following.

Stem: {stem}
Options: {options}
Claimed correct index: {correct_index} -> {correct_text}
Rule: {rule}
Derivation: {derivation}

Your job (do the math YOURSELF, do not trust the derivation):

1. Extract the visible numeric terms from the stem in order.
2. Apply the stated rule to term 1 to compute term 2. Does it match the stem?
3. Apply the rule to term 2 to compute term 3. Does it match the stem?
4. Continue for ALL visible terms.
5. Apply the rule ONE MORE time to the last visible term to compute the next term.
6. Does your computed next term equal {correct_text}?
7. Does the correct_index actually point to {correct_text}?

If EVERY check passes -> valid=true. Otherwise -> valid=false.

Common failure to watch for: the derivation uses the same multiplier/offset twice in a row
instead of incrementing it. Check each multiplier step carefully.

Respond with ONLY this JSON (no commentary):
{{"valid": true_or_false, "reason": "one sentence with the exact arithmetic you verified"}}
"""

def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in LLM output")
    return json.loads(text[start:end + 1])


def _clean_options(options):
    out = []
    for opt in options:
        s = str(opt).strip()
        s = re.sub(r"^[A-Da-d][\.\):\-]\s*", "", s)
        s = re.sub(r"^\d+[\.\):\-]\s*", "", s)
        out.append(s.strip())
    return out


def _generate_once(category: str, difficulty: int, previous_stem: str = None) -> dict:
    if previous_stem:
        previous_block = (
            'A task you just generated had this stem:\n'
            f'"{previous_stem}"\n'
            'Do NOT reuse its template, its rule, or its answer format. '
            'Invent a genuinely different item at the same difficulty level.'
        )
    else:
        previous_block = ""

    prompt = (TASK_PROMPT
        .replace("{category}", category)
        .replace("{difficulty}", str(difficulty))
        .replace("{previous_block}", previous_block))
    raw = llm.invoke(prompt).content
    data = _extract_json(raw)

    assert data["category"] == category
    assert len(data["options"]) == 4
    assert 0 <= data["correct_index"] <= 3
    assert "derivation" in data, "Model did not output derivation field"
    assert "rule" in data, "Model did not output rule field"
    data["options"] = _clean_options(data["options"])
    
    # --- FORSIRANI SHUFFLE ---
    correct_text = data["options"][data["correct_index"]]
    random.shuffle(data["options"])
    data["correct_index"] = data["options"].index(correct_text)
    if "why_wrong" in data:
        data["why_wrong"] = {} # Očisti why_wrong jer su indeksi promijenjeni
    # -------------------------

    return data



def _verify_task(task: dict) -> tuple:
    """Second-LLM verification. Returns (ok: bool, reason: str)."""
    if task["category"] != "sequences":
        return True, "skip-non-sequence"
    prompt = VERIFY_PROMPT.format(
        stem=task["stem"],
        options=task["options"],
        correct_index=task["correct_index"],
        correct_text=task["options"][task["correct_index"]],
        rule=task["rule"],
        derivation=task.get("derivation", ""),
    )
    try:
        raw = test_llm.invoke(prompt).content
        data = _extract_json(raw)
        return bool(data.get("valid", False)), data.get("reason", "")
    except Exception as e:
        return False, f"verifier-error: {e}"


def generate_task(category: str, difficulty: int, previous_stem: str = None,
                  max_retries: int = 2) -> dict:
    """Generate + verify with retry. Raises ValueError if all retries fail."""
    last = "no attempts"
    for attempt in range(max_retries + 1):
        try:
            task = _generate_once(category, difficulty, previous_stem)
            ok, reason = _verify_task(task)
            if ok:
                print(f"  [verify OK on attempt {attempt+1}]")
                return task
            print(f"  [verify FAIL on attempt {attempt+1}: {reason}]")
            last = reason
        except Exception as e:
            print(f"  [gen error on attempt {attempt+1}: {e}]")
            last = str(e)
    raise ValueError(f"Task generation failed after {max_retries+1} attempts: {last}")


def explain_answer(task: dict, user_index: int) -> str:
    prompt = EXPLAIN_PROMPT.format(
        stem=task["stem"],
        opt0=task["options"][0],
        opt1=task["options"][1],
        opt2=task["options"][2],
        opt3=task["options"][3],
        correct_index=task["correct_index"],
        correct_text=task["options"][task["correct_index"]],
        rule=task["rule"],
        derivation=task.get("derivation", ""),
        user_index=user_index,
        user_text=task["options"][user_index],
        is_correct=(user_index == task["correct_index"]),
    )
    return test_llm.invoke(prompt).content.strip()
