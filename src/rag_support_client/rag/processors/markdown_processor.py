"""
Markdown document processing module for the RAG Support application.
Optimized for technical support documentation with step-by-step instructions.
"""

from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from rag_support_client.config.config import get_settings
from rag_support_client.utils.logger import logger

settings = get_settings()


class MarkdownProcessor:
    """Processes Markdown documents with preservation of instruction structure."""

    def __init__(self) -> None:
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "title"),
                ("##", "section"),
                ("###", "subsection"),
            ],
            strip_headers=False,
            return_each_line=False,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=settings.separators,
            length_function=len,
            add_start_index=True,
        )

    def process_file(self, file_path: Path) -> list[Document]:
        """Process a single markdown file with focus on preserving instruction
        structure."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract source URL if present at the end
            source_url = None
            content_lines = content.split("\n")
            if content_lines and content_lines[-1].strip().startswith("<http"):
                source_url = content_lines[-1].strip("<>").strip()
                content = "\n".join(content_lines[:-1])

            # Base metadata
            base_metadata = {
                "source": str(file_path),
                "file_name": file_path.name,
                "page_id": file_path.stem,
                "source_url": source_url,
            }

            # Split by headers first
            header_splits = self.markdown_splitter.split_text(content)
            processed_chunks = []

            for doc in header_splits:
                # Build complete context path
                header_context = []
                if "title" in doc.metadata:
                    header_context.append(doc.metadata["title"])
                if "section" in doc.metadata:
                    header_context.append(doc.metadata["section"])
                if "subsection" in doc.metadata:
                    header_context.append(doc.metadata["subsection"])

                # Enhanced metadata
                enhanced_metadata = {
                    **base_metadata,
                    **doc.metadata,
                    "header_path": (
                        " > ".join(header_context) if header_context else None
                    ),
                    "page_title": doc.metadata.get("title", ""),
                }

                # Split content using configured settings
                chunks = self.text_splitter.split_text(doc.page_content)

                # Create documents with preserved structure
                for i, chunk in enumerate(chunks, 1):
                    chunk_metadata = {
                        **enhanced_metadata,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "is_complete_section": len(chunks) == 1,
                    }

                    processed_chunks.append(
                        Document(page_content=chunk.strip(), metadata=chunk_metadata)
                    )

            logger.debug(
                f"Processed {file_path.name}: {len(processed_chunks)} chunks created"
            )
            return processed_chunks

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            return []

    def get_context_window(
        self,
        chunks: list[Document],
        target_index: int,
        window_size: int = 1,
    ) -> str | None:
        """Get surrounding context while maintaining instruction coherence."""
        try:
            if not chunks or target_index < 0 or target_index >= len(chunks):
                return None

            # Get target chunk's header path
            target_path = chunks[target_index].metadata.get("header_path")
            if not target_path:
                return chunks[target_index].page_content

            # Collect all chunks from the same section
            related_chunks = [
                chunk
                for chunk in chunks
                if chunk.metadata.get("header_path") == target_path
            ]

            # Find position in related chunks
            try:
                current_pos = [
                    i
                    for i, c in enumerate(related_chunks)
                    if c.metadata.get("chunk_index")
                    == chunks[target_index].metadata.get("chunk_index")
                ][0]
            except IndexError:
                return chunks[target_index].page_content

            # Get window of chunks
            start_idx = max(0, current_pos - window_size)
            end_idx = min(len(related_chunks), current_pos + window_size + 1)

            return "\n\n".join(
                c.page_content for c in related_chunks[start_idx:end_idx]
            )

        except Exception as e:
            logger.error(f"Error getting context window: {str(e)}")
            return None
