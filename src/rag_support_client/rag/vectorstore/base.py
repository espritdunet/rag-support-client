"""
Base module for vector store operations.
"""

from pathlib import Path

from langchain.docstore.document import Document
from langchain.schema.embeddings import Embeddings
from langchain_chroma import Chroma

from rag_support_client.config.config import settings
from rag_support_client.rag.embeddings.ollama import get_embeddings
from rag_support_client.utils.logger import logger


class VectorStoreManager:
    """
    Manages vector store operations and configuration.
    """

    def __init__(
        self,
        embedding_function: Embeddings | None = None,
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
    ):
        """Initialize the VectorStoreManager."""
        self.embedding_function = embedding_function or get_embeddings()
        self.persist_directory = str(
            persist_directory or settings.CHROMA_PERSIST_DIRECTORY
        )
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._ensure_persist_directory()

    def _ensure_persist_directory(self) -> None:
        """Ensure the persistence directory exists."""
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def create_vectorstore(
        documents: list[Document],
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
    ) -> Chroma:
        """Create a new vector store from documents."""
        try:
            logger.info("Initializing VectorStoreManager")
            manager = VectorStoreManager(
                persist_directory=persist_directory, collection_name=collection_name
            )

            logger.info(f"Processing {len(documents)} documents through Chroma")
            logger.debug("Starting Chroma.from_documents")

            vectorstore = Chroma.from_documents(
                documents=documents,
                embedding=manager.embedding_function,
                persist_directory=manager.persist_directory,
                collection_name=manager.collection_name,
            )

            logger.info("Vectorstore created successfully")
            return vectorstore

        except Exception as e:
            logger.error(f"Error creating vectorstore: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_existing_vectorstore(
        persist_directory: str | Path | None = None,
        collection_name: str | None = None,
    ) -> Chroma:
        """Get existing vector store instance."""
        manager = VectorStoreManager(
            persist_directory=persist_directory, collection_name=collection_name
        )

        return Chroma(
            embedding_function=manager.embedding_function,
            persist_directory=manager.persist_directory,
            collection_name=manager.collection_name,
        )
