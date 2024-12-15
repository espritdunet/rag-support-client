"""
Document loader module for the RAG Support application.
Handles loading and preprocessing of Markdown documents.
"""

from pathlib import Path

from langchain.schema import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from rag_support_client.config.config import get_settings
from rag_support_client.utils.logger import logger


class DocumentLoader:
    """
    Handles loading and preprocessing of Markdown support documents.
    Optimized for technical documentation with hierarchical structure.
    """

    def __init__(self) -> None:
        """
        Initialize document loader with optimized splitting configurations.
        Uses header-based splitting for maintaining document structure,
        followed by size-based splitting for manageable chunks.
        """
        # Get settings instance
        settings_instance = get_settings()

        # Header splitting configuration
        self.headers_to_split_on: list[tuple[str, str]] = [
            ("#", "h1"),  # Document title
            ("##", "h2"),  # Main sections
            ("###", "h3"),  # Subsections
        ]

        # Header-aware markdown splitter
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False,  # Keep headers for context
            return_each_line=False,  # Keep paragraphs together
        )

        # Content splitter with optimized parameters
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings_instance.CHUNK_SIZE,
            chunk_overlap=settings_instance.CHUNK_OVERLAP,
            length_function=len,
            add_start_index=True,
            separators=settings_instance.separators,
            strip_whitespace=True,
            keep_separator=True,
        )

    def load_documents(self, directory: Path | None = None) -> list[Document]:
        """Load and process Markdown documents from directory."""
        settings_instance = get_settings()
        try:
            doc_dir = Path(directory if directory else settings_instance.MARKDOWN_DIR)
            documents: list[Document] = []

            if not doc_dir.exists():
                logger.error(f"Directory not found: {doc_dir}")
                return documents

            for file_path in doc_dir.glob("**/*.md"):
                try:
                    # Read file content as lines
                    with open(file_path, encoding="utf-8") as f:
                        content_lines = f.readlines()

                    # Extract URL from last line if present
                    source_url = None
                    if content_lines and content_lines[-1].strip().startswith("<http"):
                        source_url = content_lines[-1].strip("<>").strip()
                        if source_url.endswith(">"):
                            source_url = source_url[:-1]
                        logger.debug(f"Found source URL in {file_path}: {source_url}")
                        content = "".join(content_lines[:-1])
                    else:
                        content = "".join(content_lines)
                        logger.warning(f"No source URL found in {file_path}")

                    # First split by headers to maintain document structure
                    md_docs = self.markdown_splitter.split_text(content)

                    # Add source_url to each document before further splitting
                    for doc in md_docs:
                        doc.metadata["source_url"] = source_url

                    # Then split into size-appropriate chunks
                    chunks = self.text_splitter.split_documents(md_docs)

                    # Enrich chunks with detailed metadata
                    for chunk in chunks:
                        if source_url:
                            chunk.page_content = (
                                f"{chunk.page_content}\n\nSOURCE_URL: {source_url}"
                            )

                        chunk.metadata.update(
                            {
                                "source": str(file_path),
                                "file_name": file_path.name,
                                "page_id": file_path.stem,
                                "doc_title": chunk.metadata.get("title", ""),
                                "section": chunk.metadata.get("section", ""),
                                "subsection": chunk.metadata.get("subsection", ""),
                                "chunk_size": len(chunk.page_content),
                                "source_url": source_url,
                            }
                        )

                    documents.extend(chunks)
                    logger.debug(
                        f"Processed {file_path.name} with URL {source_url}: "
                        f"{len(chunks)} chunks"
                    )

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    continue

            # Log processing summary
            if documents:
                avg_chunk_size = sum(len(d.page_content) for d in documents) / len(
                    documents
                )
                logger.info(
                    f"Total documents processed: {len(documents)} chunks, "
                    f"average chunk size: {avg_chunk_size:.0f} characters"
                )
                # Log a sample chunk for verification
                sample = documents[0]
                logger.debug(f"Sample chunk metadata: {sample.metadata}")

            return documents

        except Exception as e:
            logger.error(f"Error in document loading: {str(e)}")
            return []
