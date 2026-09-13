"""Google Gemini chat-completion generation. The only module (besides
embedding_service, for embeddings specifically) that touches the Gemini SDK —
rag_service builds prompts and interprets results, but never calls the SDK
directly.
"""

import logging

from google import genai
from google.genai import types

from app.core.config import get_settings

# The SDK logs a notice recommending Chat.send_message for every direct
# generate_content call; we deliberately use the stateless call (we manage
# conversation history ourselves), so this notice is expected, not a warning
# about a real problem.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)


class LLMConfigurationError(Exception):
    pass


class LLMGenerationError(Exception):
    pass


def get_client() -> genai.Client:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise LLMConfigurationError(
            "GEMINI_API_KEY is not configured; the AI assistant cannot generate answers."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def generate_answer(
    *,
    system_instruction: str,
    user_prompt: str,
    client: genai.Client | None = None,
) -> str:
    """Returns the model's text response for one grounded RAG turn.

    `client` is accepted for tests to inject a mock/fake without touching the
    network; production callers should omit it.
    """
    settings = get_settings()
    active_client = client or get_client()

    try:
        response = active_client.models.generate_content(
            model=settings.chat_model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                # Generous headroom: some Gemini models spend part of the
                # budget on internal "thinking" tokens before the visible
                # answer — too small a budget silently truncates the answer.
                max_output_tokens=settings.chat_max_output_tokens,
            ),
        )
    except LLMConfigurationError:
        raise
    except Exception as exc:
        raise LLMGenerationError(f"Answer generation failed: {exc}") from exc

    text = response.text
    if not text:
        raise LLMGenerationError("The model returned an empty response.")
    return text
