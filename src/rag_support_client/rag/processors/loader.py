"""
Document loader module for the RAG Support application.
"""

from pathlib import Path

from langchain.schema import Document

from rag_support_client.config.config import settings
from rag_support_client.rag.processors.markdown_processor import MarkdownProcessor
from rag_support_client.utils.logger import logger


class DocumentLoader:
    """Handles loading and preprocessing of Markdown support documents."""

    def __init__(self) -> None:
        """Initialize document loader with processor."""
        self.processor = MarkdownProcessor()

    def load_documents(self, directory: Path | None = None) -> list[Document]:
        """
        Load and process Markdown documents.

        Args:
            directory: Optional directory path. Uses settings.MARKDOWN_DIR if not
            provided

        Returns:
            List of processed document chunks
        """
        try:
            doc_dir = directory if directory else Path(settings.MARKDOWN_DIR)
            documents: list[Document] = []

            if not doc_dir.exists():
                logger.error(f"Directory not found: {doc_dir}")
                return documents

            for file_path in doc_dir.glob("**/*.md"):
                try:
                    chunks = self.processor.process_file(file_path)
                    documents.extend(chunks)
                    logger.info(f"Successfully processed: {file_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    continue

            logger.info(f"Total documents processed: {len(documents)}")
            return documents

        except Exception as e:
            logger.error(f"Error in document loading: {str(e)}")
            return []
