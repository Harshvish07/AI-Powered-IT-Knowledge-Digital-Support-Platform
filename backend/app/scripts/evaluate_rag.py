"""RAG retrieval evaluation harness.

Loads app/evaluation/questions.json and, for each question, runs REAL
retrieval — a real Gemini query embedding and a real pgvector search against
whatever is currently in the database (typically the seeded demo knowledge
base). No mocking: this is a manual evaluation tool, not part of the
automated test suite, and it measures retrieval quality against real data.

Two kinds of questions are evaluated differently:

- Questions with an `expected_document`: measures Recall@1 (the expected
  document is the single best match) and Recall@5 (it appears anywhere in
  the top 5), using similarity_threshold=0.0 so these numbers reflect pure
  ranking quality, independent of the app's configured
  RAG_SIMILARITY_THRESHOLD.
- Questions with `expected_document: null` ("unsupported questions" —
  genuinely out of the knowledge base): measures whether the system
  correctly retrieves NOTHING once the real, configured
  RAG_SIMILARITY_THRESHOLD is applied — i.e. whether it would actually
  trigger the safe fallback in production, not just whether the nearest
  chunk happens to rank low.

"Retrieval hit rate" (reported at the end) combines both: the fraction of
ALL questions where the system did the right thing — found the right
document (Recall@5) or correctly found nothing for a question the knowledge
base was never meant to answer.

Usage:
    python -m app.scripts.evaluate_rag
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services import rag_service

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "evaluation" / "questions.json"
TOP_K = 5


class EvalQuestion(TypedDict):
    question: str
    expected_document: str | None
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

    settings = get_settings()
    db = SessionLocal()

    recall_1_hits = 0
    recall_5_hits = 0
    answerable_total = 0
    abstention_hits = 0
    unsupported_total = 0
    category_totals: dict[str, int] = defaultdict(int)
    category_correct: dict[str, int] = defaultdict(int)

    try:
        for entry in questions:
            question = entry["question"]
            expected_document = entry["expected_document"]
            topic = entry["expected_topic"]
            category_totals[topic] += 1

            if expected_document is None:
                # Unsupported question: evaluate against the REAL configured
                # threshold, since what matters is whether production would
                # actually abstain, not the raw ranking.
                unsupported_total += 1
                chunks = rag_service.retrieve_relevant_chunks(
                    db,
                    question,
                    top_k=TOP_K,
                    similarity_threshold=settings.rag_similarity_threshold,
                )
                correctly_abstained = len(chunks) == 0
                abstention_hits += int(correctly_abstained)
                category_correct[topic] += int(correctly_abstained)

                status = "HIT " if correctly_abstained else "MISS"
                print(f"[{status}] {question}")
                print("        expected:  (no document — should abstain)")
                if chunks:
                    print(
                        f"        retrieved: {[c.document_title for c in chunks]} "
                        f"(top similarity {chunks[0].similarity:.3f} >= "
                        f"threshold {settings.rag_similarity_threshold})"
                    )
                else:
                    print("        retrieved: [] (correctly abstained)")
                continue

            answerable_total += 1
            chunks = rag_service.retrieve_relevant_chunks(
                db, question, top_k=TOP_K, similarity_threshold=0.0
            )
            retrieved_titles = [chunk.document_title for chunk in chunks]

            top1_hit = bool(retrieved_titles) and retrieved_titles[0] == expected_document
            top5_hit = expected_document in retrieved_titles

            recall_1_hits += int(top1_hit)
            recall_5_hits += int(top5_hit)
            category_correct[topic] += int(top5_hit)

            status = "HIT " if top1_hit else ("in-5" if top5_hit else "MISS")
            print(f"[{status}] {question}")
            print(f"        expected:  {expected_document}")
            print(f"        retrieved: {retrieved_titles}")

        total = len(questions)
        overall_hits = recall_5_hits + abstention_hits

        print()
        print("=" * 60)
        print("Per-category results (correct / total):")
        for topic in sorted(category_totals):
            print(f"  {topic:<22} {category_correct[topic]}/{category_totals[topic]}")

        print()
        print("Overall metrics:")
        if answerable_total:
            print(
                f"  Recall@1 (answerable questions): "
                f"{recall_1_hits}/{answerable_total} ({recall_1_hits / answerable_total:.1%})"
            )
            print(
                f"  Recall@5 (answerable questions): "
                f"{recall_5_hits}/{answerable_total} ({recall_5_hits / answerable_total:.1%})"
            )
        if unsupported_total:
            print(
                f"  Correct abstention (unsupported questions): "
                f"{abstention_hits}/{unsupported_total} "
                f"({abstention_hits / unsupported_total:.1%})"
            )
        print(
            f"  Overall retrieval hit rate (all {total} questions): "
            f"{overall_hits}/{total} ({overall_hits / total:.1%})"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
