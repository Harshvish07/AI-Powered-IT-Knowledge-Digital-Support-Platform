"""RAG retrieval evaluation harness.

Loads app/evaluation/questions.json and, for each question, runs REAL
retrieval — a real Gemini query embedding and a real pgvector search against
whatever is currently in the database (typically the seeded demo knowledge
base). No mocking: this is a manual evaluation tool, not part of the
automated test suite, and it measures retrieval quality against real data.

Reports top-1 and top-5 retrieval hit rates: whether the expected document
appears as the single best match, and whether it appears anywhere in the
top-5 matches, respectively. Uses similarity_threshold=0.0 (no filtering) so
the numbers reflect pure ranking quality, independent of the app's
configured RAG_SIMILARITY_THRESHOLD.

Usage:
    python -m app.scripts.evaluate_rag
"""

import json
import sys
from pathlib import Path
from typing import TypedDict

from app.core.database import SessionLocal
from app.services import rag_service

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"
TOP_K = 5


class EvalQuestion(TypedDict):
    question: str
    expected_document: str
    expected_topic: str


def _load_questions() -> list[EvalQuestion]:
    with QUESTIONS_PATH.open(encoding="utf-8") as f:
        data: list[EvalQuestion] = json.load(f)
    return data


def main() -> int:
    questions = _load_questions()
    if not questions:
        print(f"No questions found in {QUESTIONS_PATH}")
        return 1

    db = SessionLocal()
    top1_hits = 0
    top5_hits = 0

    try:
        for entry in questions:
            question = entry["question"]
            expected_document = entry["expected_document"]

            chunks = rag_service.retrieve_relevant_chunks(
                db, question, top_k=TOP_K, similarity_threshold=0.0
            )
            retrieved_titles = [chunk.document_title for chunk in chunks]

            top1_hit = bool(retrieved_titles) and retrieved_titles[0] == expected_document
            top5_hit = expected_document in retrieved_titles

            top1_hits += int(top1_hit)
            top5_hits += int(top5_hit)

            status = "HIT " if top1_hit else ("in-5" if top5_hit else "MISS")
            print(f"[{status}] {question}")
            print(f"        expected:  {expected_document}")
            print(f"        retrieved: {retrieved_titles}")

        total = len(questions)
        print()
        print(f"Top-1 hit rate: {top1_hits}/{total} ({top1_hits / total:.1%})")
        print(f"Top-5 hit rate: {top5_hits}/{total} ({top5_hits / total:.1%})")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
