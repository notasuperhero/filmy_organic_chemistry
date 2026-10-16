"""Turn the bible tabs (bible/*.txt, exported from the Docs artifact) into index.json.

index.json holds three kinds of pieces:
  characters : every table row of Character quirks (Q..) and Filmy cast and plots (F..)
  reactions  : every reaction section of the Reactions tab, keyed by its code (H9, O4, ...)
  fixed      : sections every story needs (template, catchphrases, continuity, haveli, never-break rules)

Run again whenever the bible changes:  python build_index.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
BIBLE = HERE / "bible"


def lines(name):
    return (BIBLE / f"{name}.txt").read_text(encoding="utf-8").splitlines()


def is_row(line):
    return line.startswith("|") and line.endswith("|")


def cells(line):
    return [c.strip() for c in line.strip("|").split("|")]


def table_rows(name, prefix):
    """Every non-header table row, with its section heading and column names."""
    out, section, header, n = [], "", None, 0
    for line in lines(name):
        if not line.strip():
            continue
        if is_row(line):
            if header is None:
                header = cells(line)
                continue
            row = cells(line)
            n += 1
            text = "; ".join(f"{h}: {v}" for h, v in zip(header, row) if v and v != "–")
            out.append({"id": f"{prefix}{n}", "tab": name, "section": section,
                        "name": row[0], "text": text})
        else:
            header = None
            # short lines without a full stop are headings
            if len(line) < 80 and not line.rstrip().endswith("."):
                section = line.strip()
    return out


def reaction_sections():
    out, cur = {}, None
    code_re = re.compile(r"^([HXOPCA]\d+)\. ")
    group_heads = {"Hydrocarbons", "Haloalkanes and haloarenes", "Alcohols, phenols and ethers",
                   "Aldehydes, ketones and carboxylic acids", "Amines and diazonium salts"}
    for line in lines("reactions"):
        m = code_re.match(line)
        if m:
            cur = m.group(1)
            out[cur] = [line]
        elif line.strip() in group_heads:
            cur = None
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def between(name, start, end=None):
    """Text from the line equal to `start` up to (not including) the line equal to `end`."""
    ls = lines(name)
    i = next(k for k, l in enumerate(ls) if l.strip() == start)
    j = next((k for k, l in enumerate(ls) if k > i and end and l.strip() == end), len(ls))
    return "\n".join(ls[i:j]).strip()


def main():
    chars = table_rows("quirks", "Q") + table_rows("filmy", "F")
    reactions = reaction_sections()
    fixed = {
        "template": between("filmy", "Story template and writing rules", "The haveli"),
        "haveli": between("filmy", "The haveli", "Guests who sit on the ring"),
        "catchphrases": between("filmy", "Fixed catchphrases and continuity rules"),
        "seating_rules": between("quirks", "The benzene ring and the seating rules",
                                 "Transformations that change a group's seating quirk"),
        "never_break": between("quirks", "Never-break rules"),
    }
    index = {"characters": chars, "reactions": reactions, "fixed": fixed,
             "conversions": "\n".join(lines("conversions"))}
    (HERE / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chars)} character rows, {len(reactions)} reactions, {len(fixed)} fixed sections")


if __name__ == "__main__":
    main()
