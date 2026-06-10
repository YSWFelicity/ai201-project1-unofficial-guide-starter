"""
Milestone 3 (step 1 of 2) — RAW document loading.

This script does ONE thing: read every source document from disk and persist
its *untouched* raw text to a single consistent format (JSONL). No cleaning,
no chunking happens here -- that is deliberate. Capturing the raw text first
gives us a reproducible snapshot to clean against, so if the cleaning logic in
ingest.py changes we never have to re-fetch or re-touch the originals.

Sources are all local .txt files under documents/ (the RateMyProfessors pages
and r/rutgers threads listed in planning.md were captured to disk already).
If a source were a live URL instead, the only change would be swapping the
open()/read() below for an HTTP fetch -- the output format would stay the same.

Output: raw_documents.jsonl  (one JSON object per document)

    {
      "source_file": "chakrabarty_mousumi.txt",
      "path": "documents/rmp/chakrabarty_mousumi.txt",
      "source_type": "ratemyprofessors",
      "campus": "Newark",
      "title": "Mousumi Chakrabarty",   # professor (rmp) or thread title (reddit)
      "char_count": 6231,
      "loaded_at": "2026-06-09T20:59:00",
      "raw_text": "4.8\n/ 5\nOverall Quality Based on 13 ratings\n..."
    }

Run:  python3 load_raw.py
"""

from __future__ import annotations

import datetime as dt
import glob
import json
import os

DOCS_DIR = "documents"
OUTPUT_PATH = "raw_documents.jsonl"

# documents/<source>/... -> (source_type label, campus). Per planning.md the
# RMP professors teach Newark course numbers; the Reddit threads are New Brunswick.
SOURCE_INFO = {
    "rmp": ("ratemyprofessors", "Newark"),
    "reddit": ("reddit", "New Brunswick"),
}


def _professor_from_filename(path: str) -> str:
    """`.../chakrabarty_mousumi.txt` -> 'Mousumi Chakrabarty'."""
    stem = os.path.splitext(os.path.basename(path))[0]
    parts = stem.split("_")
    parts.reverse()
    return " ".join(p.capitalize() for p in parts)


def load_raw_documents(docs_dir: str = DOCS_DIR) -> list[dict]:
    """Read every .txt under documents/ and return one record per file with the
    raw text preserved verbatim (only the trailing newline is stripped)."""
    paths = sorted(glob.glob(os.path.join(docs_dir, "**", "*.txt"), recursive=True))
    records: list[dict] = []

    for path in paths:
        source_dir = os.path.basename(os.path.dirname(path))   # 'rmp' or 'reddit'
        if source_dir not in SOURCE_INFO:
            continue
        source_type, campus = SOURCE_INFO[source_dir]

        with open(path, encoding="utf-8") as fh:
            raw_text = fh.read()

        # A human-readable title for the record. For RMP we derive the professor
        # from the filename; for Reddit the first line is the thread title.
        # (Reading line 0 is identification, not cleaning -- raw_text is intact.)
        if source_type == "ratemyprofessors":
            title = _professor_from_filename(path)
        else:
            title = raw_text.splitlines()[0].strip() if raw_text.strip() else ""

        records.append({
            "source_file": os.path.basename(path),
            "path": path,
            "source_type": source_type,
            "campus": campus,
            "title": title,
            "char_count": len(raw_text),
            "loaded_at": dt.datetime.now().isoformat(timespec="seconds"),
            "raw_text": raw_text,
        })

    return records


def save_jsonl(records: list[dict], output_path: str = OUTPUT_PATH) -> None:
    with open(output_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    records = load_raw_documents()
    save_jsonl(records)

    total_chars = sum(r["char_count"] for r in records)
    print(f"Loaded {len(records)} documents -> {OUTPUT_PATH}")
    print(f"Total raw characters: {total_chars:,}\n")
    print(f"{'source_file':38s} {'type':18s} {'campus':14s} chars")
    print("-" * 80)
    for r in records:
        print(f"{r['source_file']:38s} {r['source_type']:18s} {r['campus']:14s} {r['char_count']:>6,}")
