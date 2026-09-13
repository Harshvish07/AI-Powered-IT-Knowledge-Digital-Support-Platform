"""Google Gemini embedding generation. The only module that touches the Gemini
SDK — API routes and other services never call it directly.
"""

from google import genai
from google.genai import types

from app.core.config import get_settings

# Gemini's embedContent endpoint caps how many texts can go in one call; batch
# to stay well under that regardless of how many chunks a document produces.
_BATCH_SIZE = 100
_TASK_TYPE = "RETRIEVAL_DOCUMENT"


class EmbeddingConfigurationError(Exception):
    pass


class EmbeddingGenerationError(Exception):
    pass


def get_client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise EmbeddingConfigurationError(
            "GEMINI_API_KEY is not configured; embeddings cannot be generated."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def generate_embeddings(
    texts: list[str], *, client: genai.Client | None = None
) -> list[list[float]]:
    """Returns one embedding vector per input text, in the same order.

    `client` is accepted for tests to inject a mock/fake without touching the
    network; production callers should omit it.
    """
    if not texts:
        return []

    settings = get_settings()
    active_client = client or get_client()

    embeddings: list[list[float]] = []
    try:
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            response = active_client.models.embed_content(
                model=settings.embedding_model,
                # list[str] is rejected by mypy against the SDK's huge Content
                # union purely due to list invariance — every element is a
                # plain str, which the API accepts (verified against the live
                # API, see test_generate_embeddings_against_real_gemini_api).
                contents=batch,  # type: ignore[arg-type]
                config=types.EmbedContentConfig(
                    output_dimensionality=settings.embedding_dimensions,
                    task_type=_TASK_TYPE,
                ),
            )
            if response.embeddings is None or len(response.embeddings) != len(batch):
                raise EmbeddingGenerationError(
                    "Gemini returned an unexpected number of embeddings for the batch."
                )
            for item in response.embeddings:
                if item.values is None:
                    raise EmbeddingGenerationError("Gemini returned an empty embedding vector.")
                embeddings.append(item.values)
    except EmbeddingConfigurationError:
        raise
    except EmbeddingGenerationError:
        raise
    except Exception as exc:
        raise EmbeddingGenerationError(f"Embedding generation failed: {exc}") from exc

    return embeddings
