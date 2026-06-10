# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

**Rutgers University computer science course & professor reviews** (multi-campus — primarily New Brunswick, with some Newark).

This guide collects student-written reviews of Rutgers CS professors and courses from RateMyProfessors professor pages and r/rutgers discussion threads. This knowledge is hard to find through official channels because the course catalog and registrar tell you what a class *covers* but never how a professor actually *teaches* it — whether exams track the lectures, whether sections are coordinated so the instructor barely matters, how a grader handles partial credit, or which professor makes a notoriously hard course manageable. That signal is scattered across hundreds of short, anonymous, and sometimes contradictory reviews, which is exactly what a retrieval system can consolidate into a direct answer.

> Note on scope: the corpus spans more than one Rutgers campus. The Reddit threads are New Brunswick (CS111/CS112 with Goel & Centeno, `ds.cs.rutgers.edu`); several RateMyProfessors professors teach Newark course numbers (CS101/102, OS332, etc.). Each source is campus-tagged in the table below so retrieval and evaluation stay honest.

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | RateMyProfessors — Mousumi Chakrabarty (CS, Newark) | 13 short reviews; highly rated (4.8); CS101/102/342, OS332, Mobile App Dev. Reviews emphasize clarity, caring, easy exams. | [ratemyprofessors.com/professor/2526357](https://www.ratemyprofessors.com/professor/2526357) · `documents/rmp/chakrabarty_mousumi.txt` |
| 2 | RateMyProfessors — Charles Edeki (CS, Newark) | Only 2 reviews, both 1-star; CS280. Sharp negative outlier — useful for testing low-coverage retrieval. | ratemyprofessors.com (search "Charles Edeki Rutgers") · `documents/rmp/edeki_charles.txt` |
| 3 | RateMyProfessors — Joseph Elliot (CS, Newark) | 11 polarized reviews (2.3 overall); CS102/251/335/347/348/490. Recurring complaint: reads off slides, weak delivery. | [ratemyprofessors.com/professor/2528771](https://www.ratemyprofessors.com/professor/2528771) · `documents/rmp/elliot_joseph.txt` |
| 4 | RateMyProfessors — Jerry Illanovsky (CS, Newark) | 17 reviews, bimodal (lots of 5s and 1s); CS101/102/198/288/335, Intensive Programming. Strong disagreement across students. | ratemyprofessors.com (search "Jerry Illanovsky Rutgers") · `documents/rmp/illanovsky_jerry.txt` |
| 5 | RateMyProfessors — Bruno Richard (CS, Newark) | 3 reviews; CS220 Data Visualization (project-heavy, R/atom, no exams). Niche elective coverage. | [ratemyprofessors.com/professor/2584799](https://www.ratemyprofessors.com/professor/2584799) · `documents/rmp/richard_bruno.txt` |
| 6 | RateMyProfessors — Nicole Richardson (CS, Newark) | 14 reviews (3.3); "Everyday Data" / data-science courses. Divisive: "tough grader but you learn a lot." | ratemyprofessors.com (search "Nicole Richardson Rutgers") · `documents/rmp/richardson_nicole.txt` |
| 7 | r/rutgers thread — "Intro to CS: Goel or Centeno" (New Brunswick) | Multi-comment thread comparing two CS111 lecturers; key fact: CS111 is coordinated across sections. | [reddit.com/r/rutgers/comments/1lmx2yk](https://www.reddit.com/r/rutgers/comments/1lmx2yk/intro_to_cs_goel_or_centeno/) · `documents/reddit/cs111_goel_centeno_threads.txt` |
| 8 | r/rutgers thread — "How is Professor Mark Russo for Data Structures (CS112)?" (New Brunswick) | Short Q&A thread; sparse direct info on Russo, more about Goel/Centeno. Tests partial-answer handling. | [reddit.com/r/rutgers/comments/1h18b2n](https://www.reddit.com/r/rutgers/comments/1h18b2n/how_is_professor_mark_russo_for_data_structures/) · `documents/reddit/cs112_mark_russo_threads.txt` |
| 9 | r/rutgers thread — "Preparation for Data Structures (CS112)" (New Brunswick) | Study-resource thread (course site, Big-O, prior exams, video links). Long, advice-dense comments. | [reddit.com/r/rutgers/comments/1i0ko6o](https://www.reddit.com/r/rutgers/comments/1i0ko6o/preparation_for_data_structures_cs_112_and/) · `documents/reddit/cs112_preparation_threads.txt` |
| 10 | r/rutgers thread — "Does it matter what CS112 professor I take" (New Brunswick) | OP deleted; comments confirm exams/assignments are course-coordinated. Tests missing-context robustness. | [reddit.com/r/rutgers/comments/1q70faz](https://www.reddit.com/r/rutgers/comments/1q70faz/does_it_matter_what_cs112_professor_i_take_in_the/) · `documents/reddit/cs112_professor_threads.txt` |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. **Cross-campus retrieval confusion.** The corpus mixes New Brunswick (Reddit: CS111/112, Goel/Centeno) and Newark (RMP: CS101/102, OS332). The two halves share almost no courses or professors, so a New-Brunswick question ("Goel or Centeno for CS111?") and a Newark professor question ("is Elliot good?") should pull from disjoint document sets. Risk: a query about "CS data structures professor" could surface a Newark review for an unrelated course, since the embedding model doesn't know the campus distinction. Mitigation to consider: store a `campus` metadata field per chunk and/or filter on it.

2. **Noisy, boilerplate-heavy Reddit documents.** The Reddit files are full of non-content tokens — `Upvote`/`Downvote`/`Award`/`Share`, promoted ads (Windows, Shane Co.), avatar lines, emoji tags — and one thread's original question is deleted, leaving comments without their prompt. If chunked raw, embeddings get diluted by boilerplate and a chunk may lack the question it answers. Mitigation: strip Reddit UI boilerplate in preprocessing and chunk at the comment level so each chunk is a self-contained opinion.

3. **Free-text comment is a thin slice of each RMP record.** In RMP files the actual opinion is one short comment line surrounded by metadata (QUALITY/DIFFICULTY/course/date/tags). Fixed-size character chunking would split mid-review or merge two professors' comments; the key signal could land at a chunk boundary. Mitigation: chunk one review per chunk and attach course/rating/professor as metadata rather than embedding it inline.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
