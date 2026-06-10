"""
Milestone 4 (embedding + retrieval stage) — turn chunks into a searchable index.

Implements the Retrieval Approach from planning.md, unchanged:

  * Embedding model: all-MiniLM-L6-v2 via sentence-transformers. 384-dim
    vectors, runs locally with no API key, 256-token input limit comfortably
    covers one review/comment.
  * Vector store: a PERSISTENT ChromaDB collection using COSINE similarity.
  * Each chunk is stored with its full source metadata (source_file,
    source_type, campus, professor/course/quality/difficulty OR
    thread_title/author, ...) so retrieval can attribute and (optionally)
    filter results.
  * Retrieval: embed the query with the same model, similarity search,
    top-k = 5.

This stage reads the chunks produced by chunk.py, embeds them once, and
upserts them into ChromaDB. retrieve() is what the generation stage (M5)
will call.

Input:  chunks.jsonl        (produced by chunk.py)
Output: chroma_db/          (persistent ChromaDB store, git-ignored)
Run:    python3 embed.py    (builds the index, then runs the 5 eval queries)
"""

from __future__ import annotations

import json

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = "chunks.jsonl"
CHROMA_DIR = "chroma_db"
COLLECTION_NAME = "rutgers_cs_reviews"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 5

# Load the embedding model once at import time. SentenceTransformer downloads
# the weights on first use and caches them locally; subsequent runs are offline.
_model = SentenceTransformer(EMBED_MODEL_NAME)


def load_chunks(chunks_path: str = CHUNKS_PATH) -> list[dict]:
    """Read the JSONL chunks emitted by chunk.py (one {id, text, metadata}/line)."""
    with open(chunks_path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def embed_text(chunk: dict) -> str:
    """Build the string that actually gets embedded for a chunk.

    The raw chunk text is the bare review/comment -- for RateMyProfessors
    reviews it contains NO professor or course name (those live only in
    metadata). That made name-anchored queries like "Bruno Richard's CS220"
    miss, because the review vectors had no name to match. We fix that by
    prefixing the key metadata into the embedded text so professor/course/
    campus land in the vector space. The RAW text is still stored separately in
    Chroma's `documents` for display and grounding -- this prefix only affects
    what gets encoded.
    """
    m = chunk["metadata"]
    if m.get("source_type") == "ratemyprofessors":
        prefix = f"{m.get('professor', '')} — {m.get('course', '')} ({m.get('campus', '')})"
    else:  # reddit: the thread title gives context (esp. for deleted-OP threads)
        prefix = f"{m.get('thread_title', '')} ({m.get('campus', '')})"
    return f"{prefix.strip(' —()')}: {chunk['text']}"


def _get_collection() -> chromadb.Collection:
    """Open (or create) the persistent cosine-similarity collection.

    PersistentClient writes to CHROMA_DIR on disk so the index survives between
    runs -- we don't re-embed every time we want to query. get_or_create means
    this is safe to call from both the build step and retrieve().

    metadata={"hnsw:space": "cosine"} sets the distance metric for the
    collection's HNSW index to cosine (Chroma defaults to L2 / squared
    Euclidean). This must be set when the collection is FIRST created; it is
    ignored if the collection already exists, which is why build_index() deletes
    and recreates the collection to guarantee the metric.
    """
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(chunks_path: str = CHUNKS_PATH) -> chromadb.Collection:
    """Embed every chunk once and (re)build the ChromaDB collection.

    We compute embeddings ourselves with all-MiniLM-L6-v2 and hand them to
    Chroma explicitly (the `embeddings=` argument) rather than letting Chroma
    pick a default embedding function -- this keeps the planning.md model choice
    authoritative and guarantees queries are embedded with the same model.
    """
    chunks = load_chunks(chunks_path)

    # Start clean so the cosine metric and contents are deterministic.
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection didn't exist yet -- fine on a first run
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]          # RAW text, for display/grounding
    metadatas = [c["metadata"] for c in chunks]
    to_embed = [embed_text(c) for c in chunks]        # metadata-prefixed, for the vector

    # encode() returns one 384-dim vector per chunk. Chroma wants plain lists.
    # We embed the prefixed text but STORE the raw documents above.
    embeddings = _model.encode(to_embed, show_progress_bar=False).tolist()

    # add() stores ids + vectors + raw text + metadata together. Parallel lists:
    # documents[i] has embeddings[i] and metadatas[i] under ids[i].
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return collection


def retrieve(query: str, k: int = TOP_K, where: dict | None = None) -> list[dict]:
    """Embed the query and return the top-k most similar chunks.

    `where` is an optional ChromaDB metadata filter, e.g.
    {"campus": "New Brunswick"} -- handy for the cross-campus confusion risk
    named in planning.md, though top-k alone is the default approach.

    Returns a list of dicts: {id, text, metadata, distance}. With cosine space,
    distance = 1 - cosine_similarity, so SMALLER distance = more similar.
    """
    collection = _get_collection()
    query_embedding = _model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k,
        where=where,
    )

    # query() returns column-oriented lists nested one level per query. We sent
    # a single query, so everything we want is at index [0].
    hits = []
    for cid, text, meta, dist in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({"id": cid, "text": text, "metadata": meta, "distance": dist})
    return hits


# The 5 evaluation questions from planning.md, used as a retrieval smoke test.
EVAL_QUESTIONS = [
    "What programming language and editor does Professor Bruno Richard's CS220 "
    "Data Visualization course use, and does it have exams?",
    "Are CS111 and CS112 at Rutgers New Brunswick coordinated across professors, "
    "and what does that mean for which professor to pick?",
    "What is the main complaint students have about Professor Charles Edeki's CS280 class?",
    "In the Goel vs. Centeno comparison for CS111, how do students describe the "
    "difference in their lecturing styles?",
    "What do students say about the difficulty and grading of Professor Mousumi "
    "Chakrabarty's intro CS courses (CS101/CS102)?",
]


def _source_label(meta: dict) -> str:
    """Compact human-readable attribution for a retrieved chunk."""
    if meta.get("source_type") == "ratemyprofessors":
        return f"{meta.get('professor')} · {meta.get('course')} · {meta['source_file']}"
    return f"{meta.get('author')} · {meta['source_file']}"


if __name__ == "__main__":
    collection = build_index()
    print(f"Built collection '{COLLECTION_NAME}' with {collection.count()} chunks "
          f"({EMBED_MODEL_NAME}, 384-dim, cosine) -> {CHROMA_DIR}/\n")

    print(f"Retrieval smoke test (top-k={TOP_K}) on the 5 eval questions:")
    for i, q in enumerate(EVAL_QUESTIONS, 1):
        print("\n" + "=" * 78)
        print(f"Q{i}. {q}")
        print("-" * 78)
        for rank, hit in enumerate(retrieve(q), 1):
            print(f"  {rank}. (dist {hit['distance']:.3f}) [{_source_label(hit['metadata'])}]")
            print(f"     {hit['text'][:120]}{'...' if len(hit['text']) > 120 else ''}")
