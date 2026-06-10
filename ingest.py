"""
Milestone 3 — Document ingestion + chunking for "The Unofficial Guide".

Implements the Chunking Strategy from planning.md:

  * Unit of meaning = ONE review (RateMyProfessors) or ONE comment (r/rutgers).
    Each becomes a single chunk -> zero overlap between distinct reviews,
    because each review is an independent opinion.
  * A review/comment longer than CHUNK_CHAR_CAP (~600 chars) falls back to a
    sliding window of CHUNK_CHAR_CAP chars with FALLBACK_OVERLAP (~100 chars)
    of overlap, so a fact straddling the cut survives in at least one chunk.
  * Preprocessing strips RMP scaffolding (rating tables, "Similar Professors",
    "Helpful / Thumbs up", uppercase tag chips) and Reddit UI noise
    (Upvote/Downvote/Award/Share/Reply, promoted ads, avatar/emoji/flair lines).
  * Each chunk carries metadata instead of inlining boilerplate:
    professor, course, quality, difficulty, campus, source_file (+ author for
    Reddit). This is what stage 3 (embedding) will store in ChromaDB.

Run directly to ingest documents/ and print a chunk report + spot-checks:

    python ingest.py
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

# --- Chunking parameters (from planning.md "Chunking Strategy") -------------
CHUNK_CHAR_CAP = 600        # ~150 tokens; comfortably under MiniLM's 256-token limit
FALLBACK_OVERLAP = 100      # ~1 sentence; ONLY used when splitting one long comment

DOCS_DIR = "documents"

# Campus tagging: per planning.md, the RMP professors teach Newark course
# numbers; the Reddit threads are all New Brunswick.
CAMPUS_BY_SOURCE = {"rmp": "Newark", "reddit": "New Brunswick"}


@dataclass
class Chunk:
    """One self-contained opinion plus its metadata."""
    text: str
    metadata: dict = field(default_factory=dict)


# ===========================================================================
# RateMyProfessors parsing
# ===========================================================================
#
# RMP files are flat text dumps. A page begins with a header block (overall
# rating, rating distribution, "Similar Professors", "N Student Ratings") that
# we skip entirely, then a sequence of review blocks. Each review block looks
# like:
#
#     QUALITY
#     5.0
#     DIFFICULTY
#     2.0
#     CS342                 <- course code
#     May 2nd, 2026         <- date
#     For Credit: Yes       }
#     Attendance: ...       }  metadata fields (order/presence varies)
#     Would Take Again: ... }
#     Grade: A              }
#     Textbook: N/A         }
#     <the comment text>    <- the actual opinion (1+ lines, sentence case)
#     HILARIOUS             }
#     CARING                }  uppercase "tag chips" -> noise
#     Helpful               }
#     Thumbs up / 0 / ...   }  vote chrome -> noise
#
# We anchor on the literal "QUALITY" line to split reviews, then parse fields.

_RMP_META_PREFIXES = (
    "For Credit:",
    "Attendance:",
    "Would Take Again:",
    "Grade:",
    "Textbook:",
    "Reviewed:",
)


def _professor_from_filename(path: str) -> str:
    """`documents/rmp/chakrabarty_mousumi.txt` -> 'Mousumi Chakrabarty'."""
    stem = os.path.splitext(os.path.basename(path))[0]   # chakrabarty_mousumi
    parts = stem.split("_")
    parts.reverse()                                       # [mousumi, chakrabarty]
    return " ".join(p.capitalize() for p in parts)


def _is_tag_chip(line: str) -> bool:
    """RMP tags are fully UPPERCASE (e.g. 'CARING', 'SKIP CLASS? YOU WON'T PASS.').
    A real comment always contains lowercase letters, so this is a safe test."""
    return line == line.upper() and any(c.isalpha() for c in line)


def _parse_rmp_file(path: str, raw: str) -> list[Chunk]:
    professor = _professor_from_filename(path)
    source_file = os.path.basename(path)
    lines = [ln.strip() for ln in raw.splitlines()]

    # Indices of every "QUALITY" marker -> start of each review block.
    starts = [i for i, ln in enumerate(lines) if ln == "QUALITY"]
    chunks: list[Chunk] = []

    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        block = lines[start:end]

        # Fixed-position fields right after the QUALITY marker:
        #   block[0]="QUALITY", block[1]=quality, block[2]="DIFFICULTY",
        #   block[3]=difficulty, block[4]=course, block[5]=date
        quality = block[1] if len(block) > 1 else ""
        difficulty = block[3] if len(block) > 3 else ""
        course = block[4] if len(block) > 4 else ""
        date = block[5] if len(block) > 5 else ""

        # The comment is the text after the metadata fields and before the
        # first tag chip / "Helpful". The block layout is:
        #   course, date, <meta fields>, <comment>, <tag chips>, vote chrome
        # so we only start collecting comment lines once we've passed at least
        # one metadata field -- this skips the date line (which is prose-like
        # and would otherwise be glued onto the front of the comment).
        comment_lines: list[str] = []
        seen_meta = False
        for ln in block[5:]:
            if not ln:
                continue
            if ln.startswith(_RMP_META_PREFIXES):
                seen_meta = True
                continue
            if ln in ("Helpful", "Thumbs up", "Thumbs down") or ln.isdigit():
                break                      # hit the vote chrome -> review done
            if _is_tag_chip(ln):
                break                      # hit the uppercase tag chips -> done
            if seen_meta:                  # past the date + meta -> real comment
                comment_lines.append(ln)

        comment = " ".join(comment_lines).strip()
        if not comment:
            continue   # a review with no free-text comment carries no opinion

        meta = {
            "source_file": source_file,
            "source_type": "ratemyprofessors",
            "professor": professor,
            "course": course,
            "quality": quality,
            "difficulty": difficulty,
            "date": date,
            "campus": "Newark",
            "author": professor,   # an RMP review is attributed to the prof's page
        }
        chunks.extend(_emit(comment, meta))

    return chunks


# ===========================================================================
# Reddit parsing
# ===========================================================================
#
# Reddit files are a title + OP body, a wall of UI chrome, then comments.
# Each comment is shaped like:
#
#     <username>            (optionally preceded by "u/<name> avatar")
#     •
#     1y ago                <- timestamp anchor
#     emoji:...  / flair    <- optional noise line(s)
#     <comment text>        <- 1+ paragraphs
#     Upvote / N / Downvote / Award|Reply / Share   <- vote chrome
#
# Promoted ads have the same avatar/name shape but say "Promoted" instead of a
# timestamp, so anchoring on the timestamp naturally skips them.

_TIMESTAMP_RE = re.compile(r"^\d+\s*(?:y|mo|w|d|h|min)\s+ago$", re.IGNORECASE)
_FLAIR_YEAR_RE = re.compile(r"^[A-Za-z][\w .]*['’]\d{2}$")   # e.g. "math '26"
_VOTE_END = "Upvote"


def _is_comment_noise(line: str) -> bool:
    """Flair / edit / badge lines that sit between the timestamp and the text."""
    if not line or line == "•":
        return True
    if line.startswith("emoji:"):
        return True
    if line.startswith("Profile Badge"):
        return True
    if line.lower().startswith("edited") and line.lower().endswith("ago"):
        return True
    if _FLAIR_YEAR_RE.match(line):
        return True
    if line in ("OP", "CS major"):
        return True
    return False


def _parse_reddit_file(path: str, raw: str) -> list[Chunk]:
    source_file = os.path.basename(path)
    lines = [ln.strip() for ln in raw.splitlines()]
    chunks: list[Chunk] = []

    # --- OP post (title + question) as its own chunk, when not deleted -------
    title = lines[0] if lines else ""
    op_body_lines: list[str] = []
    for ln in lines[1:]:
        if not ln:
            continue
        if ln.startswith("Archived post") or ln == _VOTE_END:
            break
        op_body_lines.append(ln)
    op_body = " ".join(op_body_lines)
    deleted = ("deleted by the person" in op_body) or ("this post was deleted" in op_body.lower())
    if title and not deleted:
        op_text = f"{title} — {op_body}" if op_body else title
        meta = {
            "source_file": source_file,
            "source_type": "reddit",
            "thread_title": title,
            "campus": "New Brunswick",
            "author": "OP",
            "is_op": True,
        }
        chunks.extend(_emit(op_text, meta))

    # --- Comments: anchor on each timestamp line ---------------------------
    ts_indices = [i for i, ln in enumerate(lines) if _TIMESTAMP_RE.match(ln)]
    for n, ts in enumerate(ts_indices):
        # Author = the line just before the "•" that precedes the timestamp.
        author, is_op = "unknown", False
        j = ts - 1
        while j >= 0 and (lines[j] == "" or lines[j] == "•"):
            j -= 1
        if j >= 0:
            cand = lines[j]
            if cand == "OP":
                is_op = True
                j -= 1
                while j >= 0 and (lines[j] == "" or lines[j] == "•"):
                    j -= 1
                cand = lines[j] if j >= 0 else "unknown"
            author = re.sub(r"^u/", "", cand).replace(" avatar", "").strip()

        # Body = lines after the timestamp until the next "Upvote" (or the next
        # comment's timestamp, or EOF — whichever comes first).
        next_ts = ts_indices[n + 1] if n + 1 < len(ts_indices) else len(lines)
        body_lines: list[str] = []
        for ln in lines[ts + 1:next_ts]:
            if ln == _VOTE_END:
                break
            if _is_comment_noise(ln):
                # Drop flair/edit/badge noise wherever it appears in the header.
                if not body_lines:
                    continue          # leading noise -> skip
                continue              # stray bullet between paragraphs -> skip
            if ln:
                body_lines.append(ln)

        comment = " ".join(body_lines).strip()
        if not comment:
            continue

        meta = {
            "source_file": source_file,
            "source_type": "reddit",
            "thread_title": title,
            "campus": "New Brunswick",
            "author": author,
            "is_op": is_op,
        }
        chunks.extend(_emit(comment, meta))

    return chunks


# ===========================================================================
# Sliding-window fallback (only for over-long single comments)
# ===========================================================================
def _emit(text: str, base_meta: dict) -> list[Chunk]:
    """Emit one chunk per review/comment; if it exceeds CHUNK_CHAR_CAP, split it
    into a sliding window with FALLBACK_OVERLAP overlap (the ONLY place overlap
    is applied — distinct reviews never overlap)."""
    text = text.strip()
    if len(text) <= CHUNK_CHAR_CAP:
        return [Chunk(text=text, metadata=dict(base_meta))]

    windows: list[Chunk] = []
    step = CHUNK_CHAR_CAP - FALLBACK_OVERLAP
    part = 0
    for start in range(0, len(text), step):
        piece = text[start:start + CHUNK_CHAR_CAP].strip()
        if not piece:
            continue
        meta = dict(base_meta)
        meta["window_part"] = part            # mark that this was a fallback split
        windows.append(Chunk(text=piece, metadata=meta))
        part += 1
        if start + CHUNK_CHAR_CAP >= len(text):
            break
    return windows


def chunk_text(path: str, raw: str) -> list[Chunk]:
    """Dispatch to the RMP or Reddit parser based on the document's source dir."""
    source = os.path.basename(os.path.dirname(path))   # 'rmp' or 'reddit'
    if source == "rmp":
        return _parse_rmp_file(path, raw)
    if source == "reddit":
        return _parse_reddit_file(path, raw)
    raise ValueError(f"Unknown source directory for {path!r}: {source!r}")


# ===========================================================================
# Ingestion entry point
# ===========================================================================
def load_documents(docs_dir: str = DOCS_DIR) -> list[Chunk]:
    """Read every .txt under documents/rmp and documents/reddit, clean it, and
    return the full list of chunks (one per review/comment, plus fallback
    windows for long comments)."""
    paths = sorted(glob.glob(os.path.join(docs_dir, "**", "*.txt"), recursive=True))
    all_chunks: list[Chunk] = []
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        all_chunks.extend(chunk_text(path, raw))
    return all_chunks


def _report(chunks: list[Chunk]) -> None:
    """Print a chunk-count summary and the spot-checks named in the verify plan:
    no chunk merges two professors, and each RMP chunk keeps its comment."""
    by_file: dict[str, int] = {}
    for c in chunks:
        by_file[c.metadata["source_file"]] = by_file.get(c.metadata["source_file"], 0) + 1

    print(f"\nTotal chunks: {len(chunks)}\n")
    print("Chunks per source file:")
    for fname in sorted(by_file):
        print(f"  {fname:40s} {by_file[fname]:3d}")

    fallback = [c for c in chunks if "window_part" in c.metadata]
    print(f"\nFallback-window chunks (long comments split): {len(fallback)}")

    print("\n--- Spot-check: first 2 RMP chunks (comment must keep its rating) ---")
    shown = 0
    for c in chunks:
        if c.metadata.get("source_type") == "ratemyprofessors":
            m = c.metadata
            print(f"\n[{m['professor']} | {m['course']} | Q{m['quality']}/D{m['difficulty']} | {m['campus']}]")
            print(f"  {c.text[:200]}{'…' if len(c.text) > 200 else ''}")
            shown += 1
            if shown == 2:
                break

    print("\n--- Spot-check: first 2 Reddit comment chunks ---")
    shown = 0
    for c in chunks:
        if c.metadata.get("source_type") == "reddit" and not c.metadata.get("is_op"):
            m = c.metadata
            print(f"\n[{m['author']} | {m['source_file']} | {m['campus']}]")
            print(f"  {c.text[:200]}{'…' if len(c.text) > 200 else ''}")
            shown += 1
            if shown == 2:
                break


if __name__ == "__main__":
    chunks = load_documents()
    _report(chunks)
