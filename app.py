"""
Milestone 5 (interface stage) — Gradio front-end for "The Unofficial Guide".

A thin UI over generate.answer(): a question box, the grounded answer, and a
source list that is built in Python from the retrieved chunks (see generate.py)
— so attribution is shown for every query and cannot be omitted by the model.

Run:
    python3 app.py
then open the printed local URL (default http://127.0.0.1:7860).

Requires gradio (uncomment it in requirements.txt and `pip install -r
requirements.txt`) and a GROQ_API_KEY in .env.
"""

from __future__ import annotations

import gradio as gr

from generate import answer, format_sources_md

EXAMPLES = [
    "What programming language and editor does Professor Bruno Richard's CS220 course use, and does it have exams?",
    "Are CS111 and CS112 at Rutgers New Brunswick coordinated across professors?",
    "What is the main complaint students have about Professor Charles Edeki's CS280 class?",
    "How do students compare Goel and Centeno's lecturing styles for CS111?",
    "What do students say about the difficulty and grading of Professor Mousumi Chakrabarty's intro CS courses?",
]


def respond(question: str):
    """UI callback: returns (answer_markdown, sources_markdown).

    The two outputs come from one answer() call. `sources` is assembled from
    retrieval metadata inside generate.py, never parsed from the model's text.
    """
    result = answer(question)
    return result["answer"], format_sources_md(result["sources"])


with gr.Blocks(title="The Unofficial Guide — Rutgers CS Reviews") as demo:
    gr.Markdown(
        "# The Unofficial Guide\n"
        "Ask about Rutgers CS courses and professors. Answers are grounded **only** "
        "in retrieved student reviews from RateMyProfessors and r/rutgers, with the "
        "sources listed below every answer. If the reviews don't cover your question, "
        "the assistant will say so rather than guess."
    )

    question = gr.Textbox(
        label="Your question",
        placeholder="e.g. Is Professor Chakrabarty's grading lenient?",
        lines=2,
    )
    ask_btn = gr.Button("Ask", variant="primary")

    answer_md = gr.Markdown(label="Answer")
    sources_md = gr.Markdown(label="Sources")

    gr.Examples(examples=EXAMPLES, inputs=question)

    ask_btn.click(fn=respond, inputs=question, outputs=[answer_md, sources_md])
    question.submit(fn=respond, inputs=question, outputs=[answer_md, sources_md])


if __name__ == "__main__":
    demo.launch()
