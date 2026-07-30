"""
Text chunking strategies for RAG.
Splits documents into overlapping chunks optimized for embedding and retrieval.
"""

from dataclasses import dataclass

import tiktoken


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""

    chunk_size: int = 500  # Target tokens per chunk
    chunk_overlap: int = 50  # Overlap between consecutive chunks
    min_chunk_size: int = 50  # Minimum chunk size (discard smaller)
    separator: str = "\n\n"  # Primary split separator
    encoding_name: str = "cl100k_base"  # tiktoken encoding (GPT-4/3.5)


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    content: str
    index: int
    token_count: int
    start_char: int
    end_char: int


class TextChunker:
    """
    Splits text into overlapping chunks for vector embedding.

    Strategy:
    1. Split by paragraphs (double newline)
    2. If a paragraph exceeds chunk_size, split by sentences
    3. Merge small consecutive paragraphs to fill chunks
    4. Apply overlap between chunks for context continuity
    """

    def __init__(self, config: ChunkConfig | None = None) -> None:
        self._config = config or ChunkConfig()
        self._encoding = tiktoken.get_encoding(self._config.encoding_name)

    def chunk_text(self, text: str) -> list[TextChunk]:
        """Split text into overlapping chunks."""
        if not text.strip():
            return []

        # Split into paragraphs
        paragraphs = text.split(self._config.separator)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        chunks: list[TextChunk] = []
        current_content = ""
        current_start = 0
        char_offset = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            # If single paragraph exceeds chunk size, split by sentences
            if para_tokens > self._config.chunk_size:
                # Flush current buffer
                if current_content:
                    chunks.append(self._create_chunk(
                        current_content, len(chunks), current_start
                    ))
                    current_content = ""

                # Split large paragraph into sentence-level chunks
                sentence_chunks = self._split_by_sentences(para, char_offset)
                chunks.extend(sentence_chunks)
                char_offset += len(para) + len(self._config.separator)
                current_start = char_offset
                continue

            # Check if adding this paragraph exceeds chunk size
            test_content = f"{current_content}{self._config.separator}{para}" if current_content else para
            if self._count_tokens(test_content) > self._config.chunk_size:
                # Flush current chunk
                if current_content:
                    chunks.append(self._create_chunk(
                        current_content, len(chunks), current_start
                    ))

                # Start new chunk with overlap from previous
                overlap_text = self._get_overlap_text(current_content)
                current_content = f"{overlap_text}{self._config.separator}{para}" if overlap_text else para
                current_start = char_offset
            else:
                current_content = test_content
                if not current_content.strip():
                    current_start = char_offset

            char_offset += len(para) + len(self._config.separator)

        # Flush remaining content
        if current_content and self._count_tokens(current_content) >= self._config.min_chunk_size:
            chunks.append(self._create_chunk(
                current_content, len(chunks), current_start
            ))

        return chunks

    def _split_by_sentences(self, text: str, start_offset: int) -> list[TextChunk]:
        """Split a large paragraph into sentence-based chunks."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks: list[TextChunk] = []
        current = ""
        current_start = start_offset

        for sentence in sentences:
            test = f"{current} {sentence}" if current else sentence
            if self._count_tokens(test) > self._config.chunk_size and current:
                chunks.append(self._create_chunk(current, len(chunks), current_start))
                overlap = self._get_overlap_text(current)
                current = f"{overlap} {sentence}" if overlap else sentence
                current_start = start_offset
            else:
                current = test

        if current and self._count_tokens(current) >= self._config.min_chunk_size:
            chunks.append(self._create_chunk(current, len(chunks), current_start))

        return chunks

    def _get_overlap_text(self, text: str) -> str:
        """Get the last N tokens of text for overlap."""
        tokens = self._encoding.encode(text)
        if len(tokens) <= self._config.chunk_overlap:
            return text
        overlap_tokens = tokens[-self._config.chunk_overlap:]
        return self._encoding.decode(overlap_tokens)

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self._encoding.encode(text))

    def _create_chunk(self, content: str, index: int, start_char: int) -> TextChunk:
        """Create a TextChunk with metadata."""
        return TextChunk(
            content=content.strip(),
            index=index,
            token_count=self._count_tokens(content),
            start_char=start_char,
            end_char=start_char + len(content),
        )
