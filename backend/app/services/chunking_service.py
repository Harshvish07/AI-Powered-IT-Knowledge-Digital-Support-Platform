"""Splits extracted page text into token-bounded chunks for embedding.

Paragraph boundaries (blank-line-separated) are preserved wherever possible:
a chunk is built by packing whole paragraphs until the token budget would be
exceeded, only falling back to a hard mid-paragraph split for the rare
paragraph that alone exceeds the whole chunk budget.
"""

from dataclasses import dataclass

import tiktoken

from app.services.document_parser import ExtractedPage

# Gemini doesn't publish a tiktoken-compatible tokenizer, so cl100k_base is used
# as a reasonable, widely-available approximation purely for sizing chunks —
# it doesn't need to match the embedding model's tokenizer exactly, just keep
# chunks in the right ballpark (the configured token counts are already
# "approximately" per the chunking spec).
_ENCODING_NAME = "cl100k_base"


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    token_count: int


def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _hard_split(text: str, encoding: tiktoken.Encoding, max_tokens: int) -> list[str]:
    tokens = encoding.encode(text)
    return [
        encoding.decode(tokens[start : start + max_tokens])
        for start in range(0, len(tokens), max_tokens)
    ]


def chunk_pages(
    pages: list[ExtractedPage],
    *,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
) -> list[TextChunk]:
    encoding = _encoding()

    # Flatten to (paragraph, page_number, token_count) so chunking doesn't care
    # about page boundaries except for recording which page a chunk started on.
    paragraphs: list[tuple[str, int | None, int]] = [
        (para, page.page_number, len(encoding.encode(para)))
        for page in pages
        for para in _split_paragraphs(page.text)
    ]

    chunks: list[TextChunk] = []
    window: list[tuple[str, int | None, int]] = []
    window_tokens = 0

    def finalize_window() -> None:
        if not window:
            return
        content = "\n\n".join(p[0] for p in window)
        chunks.append(
            TextChunk(content=content, page_number=window[0][1], token_count=window_tokens)
        )

    def carry_overlap() -> tuple[list[tuple[str, int | None, int]], int]:
        carried: list[tuple[str, int | None, int]] = []
        carried_tokens = 0
        for para in reversed(window):
            if carried_tokens + para[2] > chunk_overlap_tokens:
                break
            carried.insert(0, para)
            carried_tokens += para[2]
        return carried, carried_tokens

    for para_text, page_number, para_tokens in paragraphs:
        if para_tokens > chunk_size_tokens:
            finalize_window()
            window, window_tokens = [], 0
            for piece in _hard_split(para_text, encoding, chunk_size_tokens):
                chunks.append(
                    TextChunk(
                        content=piece,
                        page_number=page_number,
                        token_count=len(encoding.encode(piece)),
                    )
                )
            continue

        if window and window_tokens + para_tokens > chunk_size_tokens:
            finalize_window()
            window, window_tokens = carry_overlap()

        window.append((para_text, page_number, para_tokens))
        window_tokens += para_tokens

    finalize_window()
    return chunks
