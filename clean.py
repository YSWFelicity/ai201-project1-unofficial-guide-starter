"""
Milestone 3 (step 2 of 2) — CLEANING.

Reads the raw snapshot (raw_documents.jsonl) and strips everything that isn't
substantive content, keeping only the text the retrieval system should reason
over plus the context needed to understand it.

REMOVED (boilerplate that repeats on every page):
  RateMyProfessors  -> overall-rating header, "Would take again" %, rating
                       distribution table, "Similar Professors" list, the
                       "N Student Ratings / All courses" banner, the uppercase
                       tag chips (CARING, LECTURE HEAVY, ...), and the
                       "Helpful / Thumbs up / Thumbs down" vote chrome.
  Reddit            -> "Archived post" notice, Upvote/Downvote/Award/Reply/
                       Share buttons + counts, "Go to comments", "Sort by",
                       "Search Comments", promoted ads (Windows, Shane Co.,
                       Washington Post, Greenwood), avatar lines, emoji/flair
                       lines, "Profile Badge ..." and "Edited ... ago".

KEPT: the review/comment text, ratings (quality/difficulty), and the context
  that makes a review interpretable -- professor, course, campus, author.

Source documents are plain .txt (no HTML), so there are no HTML tags or
entities (&amp;, &nbsp;) to strip; the audit below still scans for them so the
check is honest if a future source does contain HTML.

Output: clean_documents.jsonl  (one record per source document)
Run:    python3 clean.py
"""

from __future__ import annotations

import json
import re

from ingest import extract_units   # the boilerplate-removal extractors

RAW_PATH = "raw_documents.jsonl"
OUTPUT_PATH = "clean_documents.jsonl"

# Conversational filler that is a "complete comment" but carries no domain
# signal (e.g. "All good", "no, sorry", "Thank you very much!"). Dropping these
# avoids dead-weight embeddings. Kept deliberately narrow so thin-but-real
# opinions ("Centeno is good", "I love this guy, such a good professor.")
# survive -- a length threshold can't separate those, so we match content.
_PLEASANTRY = re.compile(
    r"^(all good|no,?\s*sorry|np|yw|you'?re welcome|got it|okay?)[\s.!,]*$",
    re.IGNORECASE,
)


def _is_substantive(text: str) -> bool:
    """False for pure acknowledgments/pleasantries (no opinion, no fact)."""
    t = text.strip()
    if t.lower().startswith("thank"):     # "Thank you...", "Thanks!"
        return False
    if _PLEASANTRY.match(t):              # "All good", "no, sorry", "np", ...
        return False
    return True

# Patterns that should NOT survive cleaning -- used purely to audit the output.
_NOISE_AUDIT = {
    "HTML tag": re.compile(r"<[^>]+>"),
    "HTML entity": re.compile(r"&(?:amp|nbsp|lt|gt|quot|#\d+);"),
    "vote/nav chrome": re.compile(r"\b(?:Upvote|Downvote|Award|Promoted|"
                                  r"Thumbs (?:up|down)|Go to comments|Sort by|"
                                  r"Search Comments|Archived post)\b"),
    "emoji/flair marker": re.compile(r"emoji:|Profile Badge"),
}


def clean_documents(raw_path: str = RAW_PATH) -> list[dict]:
    """For each raw document, extract its clean units and assemble a cleaned
    record. `units` holds one cleaned review/comment with its context; we also
    join them into a single human-readable `clean_text` for inspection."""
    with open(raw_path, encoding="utf-8") as fh:
        raw_docs = [json.loads(line) for line in fh]

    cleaned: list[dict] = []
    for doc in raw_docs:
        units = extract_units(doc["path"], doc["raw_text"])

        unit_records = []
        readable_blocks = []
        for u in units:
            m = u.metadata
            if not _is_substantive(u.text):
                continue   # drop conversational filler -> no dead-weight chunk
            unit_records.append({"text": u.text, "metadata": m})
            if m["source_type"] == "ratemyprofessors":
                header = f"[{m['professor']} · {m['course']} · " \
                         f"Q{m['quality']}/D{m['difficulty']} · {m['campus']}]"
            else:
                tag = "OP" if m.get("is_op") else m["author"]
                header = f"[{tag} · {m['source_file']} · {m['campus']}]"
            readable_blocks.append(f"{header}\n{u.text}")

        cleaned.append({
            "source_file": doc["source_file"],
            "source_type": doc["source_type"],
            "campus": doc["campus"],
            "title": doc["title"],
            "raw_char_count": doc["char_count"],
            "unit_count": len(unit_records),
            "clean_char_count": sum(len(u["text"]) for u in unit_records),
            "units": unit_records,
            "clean_text": "\n\n".join(readable_blocks),
        })

    return cleaned


def save_jsonl(records: list[dict], output_path: str = OUTPUT_PATH) -> None:
    with open(output_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def audit(records: list[dict]) -> dict[str, int]:
    """Scan all cleaned text for leftover noise. Returns {label: hit_count}."""
    hits: dict[str, int] = {}
    for rec in records:
        for u in rec["units"]:
            for label, pat in _NOISE_AUDIT.items():
                if pat.search(u["text"]):
                    hits[label] = hits.get(label, 0) + 1
    return hits


if __name__ == "__main__":
    records = clean_documents()
    save_jsonl(records)

    raw_total = sum(r["raw_char_count"] for r in records)
    clean_total = sum(r["clean_char_count"] for r in records)
    print(f"Cleaned {len(records)} documents -> {OUTPUT_PATH}")
    print(f"Characters: {raw_total:,} raw  ->  {clean_total:,} kept "
          f"({100 * clean_total / raw_total:.0f}% retained, "
          f"{100 - 100 * clean_total / raw_total:.0f}% boilerplate removed)\n")

    print(f"{'source_file':38s} {'units':>5s} {'raw':>7s} {'clean':>7s}")
    print("-" * 62)
    for r in records:
        print(f"{r['source_file']:38s} {r['unit_count']:>5d} "
              f"{r['raw_char_count']:>7,} {r['clean_char_count']:>7,}")

    # --- Read one cleaned document end-to-end -----------------------------
    sample = next(r for r in records if r["source_file"] == "richard_bruno.txt")
    print("\n" + "=" * 62)
    print(f"FULL CLEANED DOCUMENT: {sample['source_file']}")
    print("=" * 62)
    print(sample["clean_text"])

    # --- Honest leftover-noise audit --------------------------------------
    print("\n" + "=" * 62)
    hits = audit(records)
    if hits:
        print("LEFTOVER NOISE DETECTED — clean further:")
        for label, n in hits.items():
            print(f"  {label}: {n} unit(s)")
    else:
        print("AUDIT CLEAN: no HTML tags, entities, vote/nav chrome, or flair "
              "markers found in any cleaned unit.")
