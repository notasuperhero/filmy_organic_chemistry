# Filmy Organic Chemistry

Class 11–12 organic chemistry, taught as Hindi-film family drama — where every joke is a real chemical fact.

> Bade Bhaiya (anhydrous AlCl₃) has arranged every wedding in the mohalla and is still single:
> *"Main sirf rishte karwata hoon."* He makes the attacker, the ring substitutes, and he goes home unchanged.
> **[AlCl₃ is a Lewis acid catalyst: it makes R⁺ from RCl and is regenerated.]**

Ask a question ("Benzene se m-nitrobenzoic acid kaise banaoge?") and get a story: the benzene ring is a joint-family
haveli that never breaks, ring hydrogens are Ramu Kaka who leaves with *"Main chalta hoon, malik"*, –COOH is a
germophobe NRI uncle who only lets guests sit one seat away (meta), and every scene is followed by the real chemistry
in brackets, with the equation.

## Why this is not just "ask ChatGPT for a story"

A chat model will happily write a fun chemistry story. It will also, sooner or later, send Nitronium to the para
position of benzoic acid, give Benzaldehyde a red Fehling's test, or rename the characters between stories. This
project is about making the stories **correct and consistent**:

1. **A character bible** (`bible/`) — every element, group, reagent and condition in NCERT Class 11–12 organic
   chemistry has fixed properties, a fixed factual "quirk" and a fixed filmy persona. 248 character rows,
   50 reactions, 28 never-break rules, ~27k words.
2. **Retrieval, not memory** — for each question only the relevant rows (~7k tokens) are given to the model, so it
   writes from the bible rather than from whatever it remembers.
3. **A checker** — a separate pass checks every bracket and catchphrase against the same bible and the never-break
   rules; failing stories are rewritten.

## How it works

```
question
   │
   ▼
1. PLAN      model solves it, picks reaction codes + character ids   (sees a 5k-token catalogue only)
2. RETRIEVE  script copies exactly those rows out of index.json       (no model)
3. WRITE     model writes the story from the retrieved rows only
4. VERIFY    model checks brackets, catchphrases, never-break rules; one rewrite if it fails
   │
   ▼
runs/<time>/  plan.json · context.md · story_v1.md · verdict.json · story_final.md
```

## The bible

| Tab | What it holds |
| --- | --- |
| `main` | 27 elements: properties, what they do and don't do |
| `reactions` | H1–H10, X1–X8, O1–O8, P1–P6, C1–C9, A1–A9 with the role of each participant |
| `quirks` | Fixed factual personality of every participant + 28 never-break rules |
| `filmy` | Hindi-film personas, stock scene per reaction type, catchphrases, continuity rules, story template |
| `naming`, `conversions`, `basics`, `biomolecules`, `solved` | NCERT question types with worked solutions |

The bible is authored in a shared doc and exported here as text. `python build_index.py` turns it into `index.json`.

## Run it

Standard library only — nothing to install.

```bash
python build_index.py                         # after the bible changes

# with Claude
export ANTHROPIC_API_KEY=...
# or with any local model in LM Studio (set context length ≥ 16k when loading)
export OPENAI_BASE_URL=http://localhost:1234/v1 STORY_MODEL=<loaded model name>

python storyteller.py "Benzene se m-nitrobenzoic acid kaise banaoge?"
python storyteller.py --context-only --plan examples/plan_m_nitrobenzoic.json "..."   # inspect retrieval only
```

`examples/reference_story_m_nitrobenzoic.md` is a hand-written reference story in the target format.

## Status

- [x] Character bible v1 (NCERT Class 11–12 organic)
- [x] Plan → retrieve → write → verify pipeline; retrieval tested
- [ ] Evaluation set: 40 NCERT questions, scored for chemical correctness and rule adherence
- [ ] Cloud model vs local model (LM Studio) comparison
- [ ] Simple web front end
- [ ] Distil verified stories into a small model for phones

## Ground rules for stories

Original writing only: Hindi-film *tropes* (bidaai, twins separated at birth, the angry young man, the strict
principal) are fine; no real film titles, dialogues, songs or actors, and no jokes built on community or regional
stereotypes.
