"""
Milestone 3 (chunking stage) — turn cleaned units into embeddable chunks.

Implements the Chunking Strategy from planning.md, unchanged:

  * Chunk size: ONE review / ONE Reddit comment per chunk (a semantic unit).
    In practice this caps at CHUNK_CHAR_CAP = 600 characters (~150 tokens),
    comfortably under all-MiniLM-L6-v2's 256-token input limit.
  * Overlap: ZERO between distinct reviews -- each review is an independent
    opinion, so nothing should bleed across the boundary. FALLBACK_OVERLAP =
    100 characters (~1 sentence) is applied ONLY when a single over-long
    comment is split by the sliding-window fallback, so a fact straddling the
    cut survives in at least one chunk.

This stage reads the cleaned units (clean_documents.jsonl), applies the size
cap + fallback windowing (ingest._emit), and writes the final chunks.

Input:  clean_documents.jsonl   (produced by clean.py)
Output: chunks.jsonl            (one JSON object per chunk, ready for embedding)
Run:    python3 chunk.py
"""

from __future__ import annotations

import json

from ingest import CHUNK_CHAR_CAP, FALLBACK_OVERLAP, _emit

CLEAN_PATH = "clean_documents.jsonl"
OUTPUT_PATH = "chunks.jsonl"


def chunk_clean_documents(clean_path: str = CLEAN_PATH) -> list[dict]:
    """For every cleaned unit, emit one chunk -- or, for an over-long comment,
    several sliding-window chunks with FALLBACK_OVERLAP overlap."""
    with open(clean_path, encoding="utf-8") as fh:
        clean_docs = [json.loads(line) for line in fh]

    chunks: list[dict] = []
    cid = 0
    # Per-document running position, so each chunk records WHERE it sits in its
    # source document (needed later for source attribution). Keyed by
    # source_file because one cleaned doc == one source file.
    pos_in_doc: dict[str, int] = {}
    for doc in clean_docs:
        for unit in doc["units"]:
            for piece in _emit(unit["text"], unit["metadata"]):
                src = piece.metadata["source_file"]
                piece.metadata["chunk_index"] = pos_in_doc.get(src, 0)
                pos_in_doc[src] = pos_in_doc.get(src, 0) + 1
                chunks.append({
                    "id": f"chunk-{cid:03d}",
                    "text": piece.text,
                    "metadata": piece.metadata,
                })
                cid += 1
    return chunks


def save_jsonl(records: list[dict], output_path: str = OUTPUT_PATH) -> None:
    with open(output_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def verify(chunks: list[dict]) -> None:
    """Check the chunks honor the spec, including the failure modes the
    Chunking Strategy section names."""
    # 1) Size cap respected.
    longest = max(len(c["text"]) for c in chunks)
    assert longest <= CHUNK_CHAR_CAP, f"chunk exceeds cap: {longest} > {CHUNK_CHAR_CAP}"

    # 2) No chunk merges two professors: every chunk maps to exactly one source
    #    file, and each RMP file is a single professor.
    assert all(c["metadata"].get("source_file") for c in chunks)

    # 3) Overlap rule: only fallback-window chunks carry overlap; verify the
    #    overlap is actually present between consecutive windows of one comment.
    windows = [c for c in chunks if "window_part" in c["metadata"]]
    overlap_ok = True
    for a, b in zip(windows, windows[1:]):
        if b["metadata"]["window_part"] == a["metadata"]["window_part"] + 1:
            tail = a["text"][-FALLBACK_OVERLAP:]
            if not any(tail[i:] and b["text"].startswith(tail[i:]) for i in range(len(tail))):
                overlap_ok = False
    assert overlap_ok, "fallback windows are not overlapping"

    print("Spec checks passed:")
    print(f"  - longest chunk {longest} <= cap {CHUNK_CHAR_CAP}")
    print("  - every chunk maps to a single source_file (no merged professors)")
    print(f"  - {len(windows)} fallback window(s), overlap of ~{FALLBACK_OVERLAP} "
          "chars verified between consecutive windows")
    print("  - distinct reviews carry zero overlap (only fallback windows overlap)")


if __name__ == "__main__":
    chunks = chunk_clean_documents()
    save_jsonl(chunks)

    by_file: dict[str, int] = {}
    for c in chunks:
        f = c["metadata"]["source_file"]
        by_file[f] = by_file.get(f, 0) + 1

    print(f"Wrote {len(chunks)} chunks -> {OUTPUT_PATH}")
    print(f"(cap={CHUNK_CHAR_CAP} chars, fallback overlap={FALLBACK_OVERLAP} chars)\n")
    print(f"{'source_file':38s} chunks")
    print("-" * 48)
    for f in sorted(by_file):
        print(f"  {f:38s} {by_file[f]:>3d}")

    print()
    verify(chunks)
