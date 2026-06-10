"""
Milestone 5 (generation stage) — grounded answer synthesis for "The Unofficial Guide".

Implements the Generation stage from planning.md's Architecture diagram:

    retrieved chunks  ->  grounding prompt  ->  Groq (Llama)  ->  answer + cited sources

Design decisions that make grounding real (not just suggested):

  * The system prompt ENFORCES grounding with hard rules: answer ONLY from the
    provided excerpts, decline ("The reviews I have don't cover that.") when they
    don't cover the question, never blend two professors/courses, and cite the
    excerpt number behind every claim. The model is told the excerpts came from
    similarity search and that some may be irrelevant — so it must ignore the
    off-topic ones rather than treat all k as authoritative.

  * Source attribution is PROGRAMMATICALLY GUARANTEED. The Sources list returned
    to the caller (and shown in the UI) is built in Python from the metadata of
    the chunks that retrieve() returned — it is NOT parsed out of the model's
    text. Even if the LLM forgets its [n] citations, the real retrieved sources
    are always surfaced and always correct. The model's inline [n] markers only
    indicate WHICH of those retrieved excerpts it actually used.

  * temperature=0 for reproducible, fact-anchored answers.

Reads GROQ_API_KEY (and optional GROQ_MODEL) from .env.

Run directly to smoke-test the 5 evaluation questions plus one out-of-corpus
question that should be declined:

    python3 generate.py
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import Groq

from embed import EVAL_QUESTIONS, TOP_K, retrieve

load_dotenv()

# Groq-hosted Llama model. Override with GROQ_MODEL in .env if you like.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# The exact phrase the model must use when the context can't answer the question.
# We keep it as a constant so the UI / tests can recognise a clean refusal.
REFUSAL = "I don't have enough information on that."

# Hard grounding rules. Note these are RULES ("must", "only", "do not"), not
# suggestions ("try to") — that is the difference between enforcing grounding and
# merely hinting at it.
SYSTEM_PROMPT = f"""You are "The Unofficial Guide," an assistant that answers questions about \
Rutgers University computer-science courses and professors using ONLY student reviews \
from RateMyProfessors and r/rutgers.

Follow these rules without exception:

1. GROUND EVERY ANSWER IN THE CONTEXT. Answer using only the numbered review \
excerpts in the CONTEXT section of the user's message. Do not use outside \
knowledge, prior training, or any assumption about Rutgers, these professors, or \
these courses that is not stated in the excerpts.

2. DECLINE WHEN UNSUPPORTED. If the excerpts do not contain enough information to \
answer, reply with exactly this sentence and nothing else: "{REFUSAL}" Do not \
guess, do not infer beyond what the text says, and do not pad a thin answer.

3. IGNORE IRRELEVANT EXCERPTS. The excerpts were pulled by similarity search, not \
hand-picked, so some may be about a different professor, course, or campus. Use \
only the excerpts that actually bear on the question. NEVER attribute one \
professor's or student's statement to another, and never merge reviews about \
different professors or courses into one claim.

4. CITE EVERY CLAIM. After each statement, cite the excerpt number(s) it came \
from in square brackets, e.g. [1] or [2][4]. A sentence that states a fact with \
no citation is not allowed.

5. REPORT CONSENSUS AND DISSENT. These are opinions and they conflict. State the \
recurring view and explicitly note notable disagreement (e.g. a lone negative \
review) rather than smoothing it over. Be concise."""


def _source_label(meta: dict) -> str:
    """Human-readable attribution for one retrieved chunk, built from metadata.

    This is the single source of truth for how a source is displayed — used both
    in the numbered CONTEXT given to the model and in the Sources list shown to
    the user, so the two always line up.
    """
    if meta.get("source_type") == "ratemyprofessors":
        prof = meta.get("professor", "Unknown professor")
        course = meta.get("course") or "course n/a"
        return f"{prof} · {course} · RateMyProfessors ({meta.get('campus', '')}) · {meta.get('source_file', '')}"
    # reddit
    title = meta.get("thread_title", "r/rutgers thread")
    author = meta.get("author", "unknown")
    return f'r/rutgers — "{title}" · comment by {author} · {meta.get("source_file", "")}'


def build_context(hits: list[dict]) -> str:
    """Format retrieved chunks into a numbered CONTEXT block for the prompt.

    Numbering here is what the model cites with [n], and it matches the order of
    `hits`, which is also the order build_sources() lists them — so [n] in the
    answer maps to source n in the Sources panel.
    """
    blocks = []
    for i, hit in enumerate(hits, 1):
        label = _source_label(hit["metadata"])
        blocks.append(f"[{i}] {label}\n\"{hit['text']}\"")
    return "\n\n".join(blocks)


def build_sources(hits: list[dict]) -> list[dict]:
    """Build the source list DETERMINISTICALLY from retrieved metadata.

    This is the guarantee: source attribution comes from what retrieve() returned,
    never from the model's text. Returns one dict per retrieved chunk with its
    citation number, display label, source file, and similarity distance.
    """
    sources = []
    for i, hit in enumerate(hits, 1):
        sources.append({
            "n": i,
            "label": _source_label(hit["metadata"]),
            "source_file": hit["metadata"].get("source_file", ""),
            "distance": hit["distance"],
        })
    return sources


def answer(question: str, k: int = TOP_K) -> dict:
    """Retrieve, ground, and generate.

    Returns {"answer": str, "sources": list[dict], "hits": list[dict]}.
    `sources` is always populated from retrieval regardless of what the model
    wrote — that is the programmatic attribution guarantee.
    """
    question = (question or "").strip()
    if not question:
        return {"answer": "Please ask a question.", "sources": [], "hits": []}

    hits = retrieve(question, k=k)

    # No retrieval at all (e.g. empty index) -> decline rather than fabricate.
    if not hits:
        return {"answer": REFUSAL, "sources": [], "hits": []}

    context = build_context(hits)
    sources = build_sources(hits)

    user_message = (
        f"CONTEXT (student reviews retrieved for this question):\n\n{context}\n\n"
        f"QUESTION: {question}\n\n"
        "Answer using only the excerpts above, citing excerpt numbers in [brackets]."
    )

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    text = completion.choices[0].message.content.strip()

    return {"answer": text, "sources": sources, "hits": hits}


def format_sources_md(sources: list[dict]) -> str:
    """Render the deterministic source list as Markdown for display."""
    if not sources:
        return "_No sources retrieved._"
    lines = ["**Sources** _(retrieved for this question; the answer's [n] markers point here)_", ""]
    for s in sources:
        lines.append(f"**[{s['n']}]** {s['label']}  \n_similarity distance {s['distance']:.3f}_")
    return "\n\n".join(lines)


if __name__ == "__main__":
    # Smoke test: the 5 eval questions should answer + cite; the out-of-corpus
    # question should be declined with the exact REFUSAL phrase.
    questions = list(EVAL_QUESTIONS) + [
        "What do students say about Professor Alan Turing's CS999 quantum computing course?"
    ]
    for i, q in enumerate(questions, 1):
        print("\n" + "=" * 80)
        print(f"Q{i}. {q}")
        print("-" * 80)
        result = answer(q)
        print(result["answer"])
        print("\n" + format_sources_md(result["sources"]).replace("  \n", " "))
