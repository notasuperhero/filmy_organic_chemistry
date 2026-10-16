"""Question in, Bollywood chemistry story out, using only the character bible.

  1. PLAN     the model solves the question and names the reaction codes and character ids it needs
              (it sees only a short catalogue: codes + titles, ids + names)
  2. RETRIEVE this script pulls exactly those rows/sections out of index.json
  3. WRITE    the model writes the story from the retrieved bible pieces only
  4. VERIFY   the model checks every [bracket] and catchphrase against the same pieces
              plus the never-break rules; failing stories are rewritten once

Usage
  python storyteller.py "Benzene se m-nitrobenzoic acid kaise banaoge?"
  python storyteller.py --plan plan.json "..."     # skip step 1, use a hand-written plan
  python storyteller.py --context-only --plan plan.json "..."   # show what step 2 retrieves, no model calls

Model backend (pick one with environment variables)
  ANTHROPIC_API_KEY=...                         -> Claude (STORY_MODEL, default claude-sonnet-5-5)
  OPENAI_BASE_URL=http://localhost:1234/v1      -> any OpenAI-compatible server (LM Studio, mlx_lm.server,
  STORY_MODEL=<model name>                         vLLM, OpenAI itself with OPENAI_API_KEY)
Outputs go to runs/<timestamp>/ : plan.json, context.md, story_v1.md, verdict.json, story_final.md
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
INDEX = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
CHARS = {c["id"]: c for c in INDEX["characters"]}
RING_CODES = {"H9", "P2", "P3", "P4", "P5", "A6", "A7", "A8", "X7"}


# ---------------------------------------------------------------- model call
def llm(system, user, max_tokens=6000):
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_BASE_URL"):
        body = {"model": os.environ.get("STORY_MODEL", "claude-sonnet-5-5"), "max_tokens": max_tokens,
                "system": system, "messages": [{"role": "user", "content": user}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
                                     {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                      "anthropic-version": "2023-06-01", "content-type": "application/json"})
        out = json.load(urllib.request.urlopen(req, timeout=600))
        return "".join(b.get("text", "") for b in out["content"])
    base = os.environ.get("OPENAI_BASE_URL", "http://localhost:1234/v1").rstrip("/")
    body = {"model": os.environ.get("STORY_MODEL", "local-model"), "max_tokens": max_tokens, "temperature": 0.7,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    headers = {"content-type": "application/json"}
    if os.environ.get("OPENAI_API_KEY"):
        headers["authorization"] = "Bearer " + os.environ["OPENAI_API_KEY"]
    req = urllib.request.Request(base + "/chat/completions", json.dumps(body).encode(), headers)
    out = json.load(urllib.request.urlopen(req, timeout=600))
    return out["choices"][0]["message"]["content"]


def strip_thinking(text):
    """Reasoning models (Sarvam-M, Qwen3, DeepSeek-R1...) print <think>...</think> before the answer."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    return text.split("</think>")[-1].strip()   # opening tag sometimes missing


def parse_json(text):
    text = strip_thinking(text)
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):           # first position where a complete JSON object parses
        if ch == "{":
            try:
                return dec.raw_decode(text, i)[0]
            except json.JSONDecodeError:
                continue
    raise ValueError("model did not return JSON:\n" + text[:800])


# ---------------------------------------------------------------- step 1: plan
def catalogue():
    rx = "\n".join(v.splitlines()[0] for k, v in sorted(INDEX["reactions"].items()))
    rows, last = [], None
    for c in INDEX["characters"]:
        if c["section"] != last:
            rows.append(f"\n## {c['tab']} / {c['section']}")
            last = c["section"]
        rows.append(f"{c['id']}: {c['name'][:90]}")
    return rx, "\n".join(rows)


PLAN_SYSTEM = """You plan chemistry stories for Class 11-12 organic chemistry (NCERT).
You get a question, the list of reaction codes, a catalogue of character ids, and the Conversions tab.
1. Solve the question correctly, step by step (reagents, conditions, major product).
2. Pick the reaction codes that the solution uses.
3. Pick EVERY character id that will appear: for each participant pick its Q row (the factual quirk)
   AND its F row (the filmy persona) when one exists; add the F rows of the stock scene for each
   reaction type and the F catchphrase rows of characters who speak. Also pick conditions
   (cold room, dry ether, light...) and the trap a student could fall into, if the question has one.
Return ONLY JSON:
{"answer": "...", "steps": [{"equation": "...", "conditions": "...", "code": "H9"}],
 "trap": "the common wrong answer and why, or empty",
 "reaction_codes": ["H9", ...], "character_ids": ["Q12", "F23", ...], "ring": true}"""


def plan(question):
    rx, cat = catalogue()
    user = (f"QUESTION: {question}\n\nREACTION CODES:\n{rx}\n\nCONVERSIONS TAB:\n{INDEX['conversions']}"
            f"\n\nCHARACTER CATALOGUE:{cat}")
    return parse_json(llm(PLAN_SYSTEM, user, 3000))


# ---------------------------------------------------------------- step 2: retrieve
def context(p):
    fx = INDEX["fixed"]
    ids = list(dict.fromkeys(p.get("character_ids", [])))
    missing = [i for i in ids if i not in CHARS]
    ids = [i for i in ids if i in CHARS]
    ring = p.get("ring") or bool(RING_CODES & set(p.get("reaction_codes", [])))
    parts = ["# STORY TEMPLATE AND WRITING RULES\n" + fx["template"]]
    if ring:
        parts += ["# THE HAVELI (use for every ring story)\n" + fx["haveli"],
                  "# SEATING RULES (facts)\n" + fx["seating_rules"]]
    parts.append("# CHARACTERS IN THIS STORY (filmy persona = F rows, facts = Q rows; Q rows always win)\n" +
                 "\n".join(f"- [{CHARS[i]['id']}] ({CHARS[i]['section']}) {CHARS[i]['text']}" for i in ids))
    parts.append("# REACTIONS USED\n" + "\n\n".join(INDEX["reactions"][c] for c in p.get("reaction_codes", [])
                                                     if c in INDEX["reactions"]))
    parts.append("# CATCHPHRASES AND CONTINUITY RULES\n" + fx["catchphrases"])
    return "\n\n".join(parts), missing


# ---------------------------------------------------------------- step 3: write
WRITE_SYSTEM = """You write one story that teaches a Class 11-12 organic chemistry question through a Hindi-film
style family drama. You may ONLY use the characters, quirks, scenes and facts in the BIBLE below.
- Follow the story template exactly (question, cast with [chemistry], seat map for ring stories,
  scenes each followed by a [bracket: plain words + equation], figures, Daadi's closing line, summary).
- Use each character's filmy name and catchphrase exactly as written. Do not invent new characters;
  if you need one that is not in the bible, write NEED-CHARACTER: <what> at the very end instead.
- Every joke must be a fact from the bible. Dialogue in simple Hinglish, short sentences.
- The chemistry in brackets must match the solution plan and the bible exactly.

BIBLE
"""


def write(question, p, ctx, feedback=""):
    user = f"QUESTION: {question}\n\nSOLUTION PLAN:\n{json.dumps(p, ensure_ascii=False, indent=1)}"
    if feedback:
        user += "\n\nA CHECKER FOUND THESE PROBLEMS IN YOUR LAST DRAFT. Fix every one and rewrite the full story:\n" + feedback
    return strip_thinking(llm(WRITE_SYSTEM + ctx, user, 6000))


# ---------------------------------------------------------------- step 4: verify
VERIFY_SYSTEM = """You check a chemistry story against its bible. Be strict and specific.
Check: (1) every [bracket] and equation is chemically correct and matches the bible (reagents, conditions,
major product, orientation); (2) no character does something its Q row or the never-break rules forbid;
(3) filmy names and catchphrases are used exactly and only when the fact behind them is true;
(4) the template order is followed and ring stories have the seat map and product figure;
(5) no invented characters, no real films/actors/songs, no community or regional stereotypes.
Return ONLY JSON: {"pass": true/false, "problems": [{"where": "scene 2", "what": "...", "fix": "..."}]}

BIBLE
"""


def verify(story, ctx):
    rules = "# NEVER-BREAK RULES\n" + INDEX["fixed"]["never_break"]
    return parse_json(llm(VERIFY_SYSTEM + ctx + "\n\n" + rules, "STORY TO CHECK:\n" + story, 3000))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--plan", help="use this plan JSON instead of asking the model")
    ap.add_argument("--context-only", action="store_true", help="print the retrieved context and stop")
    a = ap.parse_args()

    out = HERE / "runs" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    p = json.loads(Path(a.plan).read_text(encoding="utf-8")) if a.plan else plan(a.question)
    (out / "plan.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    ctx, missing = context(p)
    (out / "context.md").write_text(ctx, encoding="utf-8")
    if missing:
        print("warning: unknown character ids", missing, file=sys.stderr)
    print(f"context: {len(ctx):,} characters (~{len(ctx) // 3:,} tokens) -> {out / 'context.md'}")
    if a.context_only:
        return

    story = write(a.question, p, ctx)
    (out / "story_v1.md").write_text(story, encoding="utf-8")
    verdict = verify(story, ctx)
    (out / "verdict.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")
    if not verdict.get("pass"):
        print(f"checker found {len(verdict.get('problems', []))} problems, rewriting once")
        story = write(a.question, p, ctx, json.dumps(verdict["problems"], ensure_ascii=False, indent=1))
        verdict2 = verify(story, ctx)
        (out / "verdict2.json").write_text(json.dumps(verdict2, ensure_ascii=False, indent=1), encoding="utf-8")
        if not verdict2.get("pass"):
            print("still failing after one rewrite; see verdict2.json")
    (out / "story_final.md").write_text(story, encoding="utf-8")
    print(f"story -> {out / 'story_final.md'}")


if __name__ == "__main__":
    main()
