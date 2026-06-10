# The Unofficial Guide — Project 1

**🎥 Video walkthrough:** [Demo video (Google Drive)](https://drive.google.com/file/d/1o5dSzSEWgBtAt-a2xU3JKHwWYkPyX4-n/view?usp=sharing)

---

## Domain

**Rutgers University computer science course & professor reviews** (multi-campus — primarily New Brunswick, with some Newark).

The system makes searchable what students actually say about Rutgers CS professors and courses, gathered from RateMyProfessors and r/rutgers. This is valuable and hard to find officially because the registrar and course catalog describe what a class covers but never how it is taught — whether exams follow the lectures, whether sections are coordinated so the instructor hardly matters, how strictly a professor grades, or who makes a notoriously hard course survivable. That knowledge lives in hundreds of short, anonymous, contradictory reviews that a retrieval system can consolidate into one grounded answer.

---

## Document Sources

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Mousumi Chakrabarty (CS, Newark) | RateMyProfessors page | [/professor/2526357](https://www.ratemyprofessors.com/professor/2526357) · `documents/rmp/chakrabarty_mousumi.txt` |
| 2 | Charles Edeki (CS, Newark) | RateMyProfessors page | `documents/rmp/edeki_charles.txt` (search "Charles Edeki Rutgers") |
| 3 | Joseph Elliot (CS, Newark) | RateMyProfessors page | [/professor/2528771](https://www.ratemyprofessors.com/professor/2528771) · `documents/rmp/elliot_joseph.txt` |
| 4 | Jerry Illanovsky (CS, Newark) | RateMyProfessors page | `documents/rmp/illanovsky_jerry.txt` (search "Jerry Illanovsky Rutgers") |
| 5 | Bruno Richard (CS, Newark) | RateMyProfessors page | [/professor/2584799](https://www.ratemyprofessors.com/professor/2584799) · `documents/rmp/richard_bruno.txt` |
| 6 | Nicole Richardson (CS, Newark) | RateMyProfessors page | `documents/rmp/richardson_nicole.txt` (search "Nicole Richardson Rutgers") |
| 7 | "Intro to CS: Goel or Centeno" (New Brunswick) | r/rutgers thread | [reddit.com/r/rutgers/.../1lmx2yk](https://www.reddit.com/r/rutgers/comments/1lmx2yk/intro_to_cs_goel_or_centeno/) · `documents/reddit/cs111_goel_centeno_threads.txt` |
| 8 | "Professor Mark Russo for CS112?" (New Brunswick) | r/rutgers thread | [reddit.com/r/rutgers/.../1h18b2n](https://www.reddit.com/r/rutgers/comments/1h18b2n/how_is_professor_mark_russo_for_data_structures/) · `documents/reddit/cs112_mark_russo_threads.txt` |
| 9 | "Preparation for Data Structures (CS112)" (New Brunswick) | r/rutgers thread | [reddit.com/r/rutgers/.../1i0ko6o](https://www.reddit.com/r/rutgers/comments/1i0ko6o/preparation_for_data_structures_cs_112_and/) · `documents/reddit/cs112_preparation_threads.txt` |
| 10 | "Does it matter what CS112 professor I take" (New Brunswick) | r/rutgers thread | [reddit.com/r/rutgers/.../1q70faz](https://www.reddit.com/r/rutgers/comments/1q70faz/does_it_matter_what_cs112_professor_i_take_in_the/) · `documents/reddit/cs112_professor_threads.txt` |

---

## Chunking Strategy

**Chunk size:** One review (RateMyProfessors) or one comment (r/rutgers) per chunk — a *semantic* unit rather than a fixed character window. In practice this caps at ~600 characters (≈150 tokens); a comment longer than that (only the advice-dense replies in the CS112 prep thread hit this) falls back to a sliding window of 600 characters.

**Overlap:** Zero between distinct reviews — each review is an independent opinion, so nothing should bleed across the boundary. ~100 characters (~1 sentence) of overlap is applied *only* on the fallback window split inside a single over-long comment, so a fact straddling the cut survives in at least one chunk. (3 of the 90 chunks are such fallback windows.)

**Preprocessing before chunking:** RMP scaffolding is stripped — rating-distribution tables, "Similar Professors", "Helpful / Thumbs up" vote chrome, and the uppercase tag chips (CARING, etc.) — keeping only the free-text comment, with `quality`/`difficulty`/`course`/`date` lifted into metadata. Reddit UI noise is stripped too — `Upvote`/`Downvote`/`Award`/`Share`/`Reply`, promoted ads, avatar lines, emoji/flair lines — and each comment is keyed off its timestamp so the author and body are kept and the chrome dropped. (See [`ingest.py`](ingest.py).)

**Why these choices fit your documents:** This is a review-heavy corpus, not a long FAQ — the unit of meaning is one review/comment, often 1–4 sentences. A fixed-size character splitter (200 or 500 chars) would do real damage: it would sever a review's comment from its rating, or merge two different professors'/students' opinions into one chunk, and the key signal would routinely land on a boundary. Splitting on the natural review/comment delimiter keeps each chunk a self-contained opinion and lets professor/course/quality/difficulty/campus ride along as metadata instead of being embedded as inline boilerplate. Chunks would be **too small** if a query like "is Chakrabarty's grading lenient?" pulled a chunk holding only the rating numbers without the sentence explaining them; **too large** if one chunk spanned two professors and the model misattributed a complaint — both failure modes this strategy avoids.

**Final chunk count:** **90** chunks across 10 source files (62 RateMyProfessors reviews, 28 Reddit comments/OP posts; 3 are fallback windows from long comments).

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, producing 384-dimensional embeddings, stored and queried in **ChromaDB with cosine similarity**, top-k = 5. It runs locally with no API key or cost, embeds the whole corpus in seconds, and its 256-token input limit comfortably covers a single review or comment. **One revision during implementation:** the first build embedded each chunk's bare text, which broke name-anchored queries — RMP review comments contain no professor or course name (those live only in metadata), so "Bruno Richard's CS220" had nothing to match and returned zero Richard chunks. The fix is **metadata-prefixed embedding**: each chunk is encoded as `"<professor> — <course> (<campus>): <review text>"` (RMP) or `"<thread_title> (<campus>): <comment text>"` (Reddit), so professor/course/campus land in the vector space. The **raw** review text is still stored separately in Chroma's `documents` for display and grounding — only the encoded string carries the prefix (see `embed_text()` in [`embed.py`](embed.py)). After this change all five evaluation questions retrieve their expected source.

**Why top-k = 5:** each chunk is one student's anecdote, but a "what do students say" question is about *consensus*. k=1–2 collapses the answer to a single voice and misses outliers (e.g. Chakrabarty's lone dissenting review); k=15+ pulls off-topic and cross-campus reviews into context and invites the model to blend unrelated professors. k=5 is the deliberate middle — enough to synthesize, few enough to stay on-target.

**Production tradeoff reflection:** If cost weren't a constraint and this served real users, I'd weigh: **(1) accuracy on short, opinionated text** — MiniLM is a strong general model, but a larger one (`bge-large-en-v1.5`) or a hosted model (`text-embedding-3-large`) would better separate sentiment-laden phrasing like "tough grader but you learn a lot" from genuinely negative reviews, which directly relates to the cross-professor crowding failure documented below. **(2) Context length** — MiniLM truncates at 256 tokens, fine for reviews but it would clip the long advice comments in the CS112 prep thread; a long-context model would embed those whole. **(3) Latency vs. local control** — MiniLM is instant and offline; an API model adds per-query latency and a network dependency but raises accuracy. **(4) Multilingual** — not relevant here (the corpus is entirely English), so I would *not* pay for multilingual capacity. Net: for a real deployment I'd likely move to `bge-large-en-v1.5` (still local, better domain separation) before reaching for a paid API, trading a little speed for retrieval quality.

---

## Grounded Generation

**System prompt grounding instruction:**

Grounding is enforced by the system prompt in [`generate.py`](generate.py), which gives the model hard rules rather than soft suggestions. The model is told it answers questions about Rutgers CS courses/professors using **only** the numbered student-review excerpts in the `CONTEXT` section of the user message, with five non-negotiable rules:

1. **Ground every answer in the context** — use only the provided excerpts; no outside knowledge or training-data assumptions about Rutgers, the professors, or the courses.
2. **Decline when unsupported** — if the excerpts don't contain enough to answer, reply with *exactly*: "I don't have enough information on that." (and nothing else). No guessing, no padding a thin answer.
3. **Ignore irrelevant excerpts** — the excerpts come from similarity search (top-k=5), not hand-picking, so some may be about a different professor/course/campus. The model must use only the ones that bear on the question and **never blend two professors' or students' statements** into one claim.
4. **Cite every claim** — each statement must carry the excerpt number(s) it came from in brackets, e.g. `[1]` or `[2][4]`; a fact with no citation is not allowed.
5. **Report consensus *and* dissent** — state the recurring view and explicitly flag notable disagreement (e.g. a lone negative review) rather than smoothing it over.

The structural choices that back this up: retrieved chunks are passed as a **numbered** `CONTEXT` block (`build_context()`), the call runs at **temperature 0** for reproducible, fact-anchored answers, and the refusal string is a named constant (`REFUSAL`) so the rule and the code agree on the exact wording. Verification: an out-of-corpus question ("Professor Alan Turing's CS999") still retrieves 5 chunks by similarity, yet the model returns the exact refusal phrase instead of bending those chunks into an answer — grounding holds even when retrieval returns something.

**How source attribution is surfaced in the response:**

Attribution is surfaced **two ways**, with the second as a hard guarantee:

1. *In the answer text* — rule 4 above makes the model cite the excerpt number(s) behind each claim inline (`[n]`).
2. *Programmatically, after generation* — `build_sources()` constructs the source list directly from the **metadata of the chunks `retrieve()` returned**, not from the model's text, and `format_sources_md()` appends it below every answer. Each entry shows the document the claim could come from: `professor · course · RateMyProfessors (campus) · source_file` for RMP reviews, or `r/rutgers — "thread title" · comment by <author> · source_file` for Reddit comments, plus the similarity distance.

Because the Sources panel is built from retrieval rather than parsed from the model's output, the document names are surfaced for **every** query and cannot be hallucinated or silently dropped even if the model forgets a `[n]`. The model's inline `[n]` markers only indicate *which* of the listed sources it actually used; `build_context()` and `build_sources()` number the chunks in the same order, so `[2]` in the answer maps to source `[2]` in the panel. Example (eval Q1): the answer "...uses R and the Atom editor [2]... no traditional exams except a final project [2]" pairs with an appended `[2] Bruno Richard · CS220 · RateMyProfessors (Newark) · richard_bruno.txt`.

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Language/editor in Bruno Richard's CS220, and exams? | R + Atom; project/homework-heavy, no exams except the final project. | "Uses R and the Atom editor [2]; no traditional exams except a final project [2]; lectures are vital, don't miss more than one [1]." Top source: `richard_bruno.txt`. | Relevant | Accurate |
| 2 | Are CS111/CS112 coordinated, and what does that mean for picking a professor? | Yes — both coordinated; projects/exams/recitations same across sections, so professor choice is about lecture style only. | "Coordinated across professors — projects, exams, recitations are the same [1][4]; professor doesn't significantly affect workload [2][4]; pick a section by recitation time [5]." Sources: `cs111_goel_centeno`, `cs112_professor`. | Relevant | Accurate |
| 3 | Main complaint about Charles Edeki's CS280? | Lectures don't match exams (questions from textbook, chapters skipped/out of order) **and** reads off slides / off-topic tangents → self-taught. | "Only reads off slides, goes off topic, tells long personal stories; essentially self-taught [1]." Missed the exam-mismatch complaint. Top source: `edeki_charles.txt`. | Partially relevant | Partially accurate |
| 4 | Goel vs. Centeno CS111 lecturing styles? | Goel structured/easy to follow; Centeno slower pace, occasionally off-topic, is the coordinator; both kind and helpful. | "Centeno slower-paced [2]; both explain well with examples [2]; comes down to preference since content is coordinated [1][5]; Goel good at explaining [1]." Source: `cs111_goel_centeno`. | Relevant | Accurate |
| 5 | Difficulty/grading of Mousumi Chakrabarty's CS101/CS102? | Low difficulty, lenient grading, mostly A/A+; recurring "easy, caring, clear"; one dissenting review on weak teaching. | "Lenient/easy to pass [1][3][5]; CS101 'study and go to class, you'll pass' with fair grading [3]; **dissent** noted — one student found the curriculum hard to grasp [1]." Source: `chakrabarty_mousumi.txt`. | Relevant | Accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**Summary:** 4 of 5 fully accurate and well-grounded; Q3 was partially accurate due to a retrieval-recall gap (only one of Edeki's two reviews reached the top-5), analyzed in detail below. An out-of-corpus control question (a professor not in the documents) was correctly declined with "I don't have enough information on that." rather than answered from general knowledge.

---

## Failure Case Analysis

**Question that failed:** "What is the main complaint students have about Professor Charles Edeki's CS280 class?" (evaluation Q3).

**What the system returned:** A grounded, correctly-cited, but **incomplete** answer — that Edeki only reads off slides, goes off topic, and tells long personal stories, making the class "essentially self-taught" [1]. It missed the other half of the expected answer: that **exams don't track the lectures** — test questions are pulled from the textbook, chapters are skipped, and material from one chapter shows up on a different chapter's test ("Chp 8 stuff will be on a chp 12 test... he'll skip chap 4-9"). The answer was right about what it covered; it just didn't cover everything.

**Root cause (tied to a specific pipeline stage): the Retrieval stage, not generation.** Edeki has exactly two reviews in the index, stored as separate chunks per the one-review-per-chunk strategy: `chunk-043` (reads-off-slides / self-taught) and `chunk-042` (exams-don't-match-lectures). Only `chunk-043` reached the top-5; the other four slots were filled by *other* professors' harshly-negative reviews (Illanovsky, Elliot), and `chunk-042` was pushed out. The reason is a cross-professor crowding effect in the shared embedding space: the query "main *complaint* about Edeki" sits very close to generic strongly-negative phrasing ("Awful professor", "Absolute joke of a professor"), so several other professors' negativity out-scored Edeki's own second review, which opens on a tangent about classroom remarks before getting to the exam mechanics and reads as less prototypically "a complaint." This is a same-corpus variant of the cross-campus confusion risk named in planning.md — different professor, semantically similar sentiment. Generation behaved correctly throughout: it grounded only in the retrieved text, cited it, and (rightly) ignored the four other professors' chunks instead of blending them in. The information loss happened before the model ever saw the context.

**What you would change to fix it:** Add a **metadata pre-filter** for professor-specific questions. `retrieve()` already accepts a ChromaDB `where=` argument ([`embed.py`](embed.py)); a light entity-detection step that maps "Edeki" → `where={"professor": "Charles Edeki"}` would make all five retrieved slots come from Edeki, surfacing **both** reviews and letting the answer report the full complaint. This is preferable to simply raising top-k, which would pull in *more* cross-professor noise rather than less. A lighter-touch alternative is to weight the professor name more heavily in the embedding prefix so a named-professor query separates that professor's reviews from the general pool of negative reviews; the metadata filter is the more reliable fix because it makes the professor constraint exact rather than relying on embedding proximity.

---

## Spec Reflection

**One way the spec helped you during implementation:** The Chunking Strategy section named both failure modes in advance — "too small" (a chunk holding only rating numbers without the explaining sentence) and "too large" (one chunk spanning two professors). Having those written down turned implementation into verification: when I built `ingest.py` I wasn't guessing whether the splitter was right, I was checking it against two concrete bad outcomes the spec had already defined. The spot-check report (no chunk merges two professors; each RMP chunk keeps its comment with its rating) maps one-to-one onto those predictions, so the spec gave me my acceptance test for free.

**One way your implementation diverged from the spec, and why:** The original Retrieval Approach embedded each chunk's **bare text**. During Milestone 4 testing this failed badly on name-anchored queries — RMP comments contain no professor or course name (those live only in metadata), so "Bruno Richard's CS220" matched nothing and returned zero Richard chunks. I diverged to **metadata-prefixed embedding**: the encoded string now carries `"<professor> — <course> (<campus>): <text>"` while the raw text is still stored for grounding. I updated planning.md to record this rather than letting the doc drift. The divergence was driven by the evaluation questions themselves — the spec's own Q1 (Richard/CS220) was the test that exposed the gap, which is exactly the feedback loop the planning doc was meant to create.

---

## AI Usage

**Instance 1 — Generation + interface (Milestone 5)**

- *What I gave the AI:* My planning.md Architecture diagram and Retrieval Approach section, the existing `retrieve()` signature from `embed.py` (returns `{id, text, metadata, distance}`), and the README's Grounded Generation requirement — specifically that answers must come only from retrieved context, decline when uncovered, and cite sources.
- *What it produced:* `generate.py` (a grounding system prompt, numbered-context assembly, a Groq `llama-3.3-70b-versatile` call at temperature 0, and a deterministic source list) plus `app.py` (a Gradio `gr.Blocks` UI).
- *What I changed or overrode:* I directed that **source attribution be programmatically guaranteed** rather than left to the model — `build_sources()` builds the Sources panel from retrieved metadata, so document names appear for every query even if the model drops a `[n]` citation. I also tightened the refusal from a soft suggestion into a hard rule with an exact required phrase ("I don't have enough information on that."), kept as a named constant so the prompt and the tests agree on the wording.

**Instance 2 — Chunking (Milestone 3)**

- *What I gave the AI:* My Chunking Strategy section plus two sample files (`chakrabarty_mousumi.txt`, `cs111_goel_centeno_threads.txt`), with the list of RMP/Reddit boilerplate to strip and the metadata fields to attach.
- *What it produced:* `load_documents()` and `chunk_text()` — a delimiter-based splitter emitting one chunk per review/comment with a metadata dict, plus a sliding-window fallback for long comments.
- *What I changed or overrode:* The first attempt leaned toward a fixed-size character splitter; I overrode it to anchor on the natural review/comment delimiter (the "QUALITY" marker for RMP, the timestamp line for Reddit) because my documents are short independent reviews, not long prose — a fixed window would have merged two professors' opinions or split a comment from its rating, the exact failure modes my spec named. I verified with the chunk-count spot-check (90 chunks, none merging two professors).
