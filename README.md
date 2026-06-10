# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section *after* you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

<!-- What topic or category of knowledge does your system cover?
     Why is this knowledge valuable, and why is it hard to find through official channels?
     Example: "Student reviews of CS professors at [university] — useful because official
     course descriptions don't reflect teaching style, exam difficulty, or workload." -->

**Rutgers University computer science course & professor reviews** (multi-campus — primarily New Brunswick, with some Newark).

The system makes searchable what students actually say about Rutgers CS professors and courses, gathered from RateMyProfessors and r/rutgers. This is valuable and hard to find officially because the registrar and course catalog describe what a class covers but never how it is taught — whether exams follow the lectures, whether sections are coordinated so the instructor hardly matters, how strictly a professor grades, or who makes a notoriously hard course survivable. That knowledge lives in hundreds of short, anonymous, contradictory reviews that a retrieval system can consolidate into one grounded answer.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

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

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**

**Overlap:**

**Why these choices fit your documents:**

**Final chunk count:**

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

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

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
