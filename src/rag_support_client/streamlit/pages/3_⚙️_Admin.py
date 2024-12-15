"""Admin interface for RAG system management"""

import asyncio
import time
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any, cast

import pandas as pd
import psutil
from chromadb.api.models.Collection import Collection

import streamlit as st
from rag_support_client.config.config import get_settings
from rag_support_client.rag.document_loader import DocumentLoader
from rag_support_client.rag.vectorstore.base import VectorStoreManager
from rag_support_client.streamlit.components.base import Page
from rag_support_client.utils.logger import logger
from rag_support_client.utils.monitoring import (
    SystemStatus,
    check_chromadb_health,
    check_ollama_health,
    export_configuration,
    get_current_configuration,
    reset_chromadb,
)
from streamlit.runtime.uploaded_file_manager import UploadedFile


class AdminPage(Page):
    """Admin page component with improved state management."""

    def __init__(self) -> None:
        """Initialize admin page with required components."""
        super().__init__(
            title="Admin Dashboard",
            icon="⚙️",
            layout="wide",
        )
        self._initialize_session_state()

    def _initialize_session_state(self) -> None:
        """Initialize or reset session state variables."""
        defaults: dict[str, bool | int | dict | str | None] = {
            "metrics_update_interval": 30,
            "show_system_metrics": True,
            "config_changed": False,
            "last_metrics_update": 0,
            "last_status_check": None,
            "system_status": None,
            "settings_values": {},
            "reset_mode": "embeddings_only",
            "documents_loaded": False,
            "vectorstore_initialized": False,
        }

        # Only set defaults for missing keys
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _format_bytes(self, size: float) -> str:
        """Format bytes to human readable string."""
        size_float = float(size)  # Convert to float for division
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} PB"

    def _get_collection(self) -> Collection:
        """Get ChromaDB collection with error handling."""
        try:
            manager = VectorStoreManager()
            vectorstore = manager.get_existing_vectorstore()
            return cast(Collection, vectorstore._collection)
        except Exception as e:
            logger.error(f"Failed to get ChromaDB collection: {e}")
            st.error("Failed to connect to ChromaDB")
            raise

    def _handle_reset(self) -> None:
        """Handle vectorstore reset with validation."""
        try:
            # Reset mode selection
            mode = st.radio(
                "Reset Mode",
                ["Embeddings Only", "Complete Reset (including documents)"],
                key="reset_mode_selection",
            )
            st.session_state.reset_mode = (
                "complete"
                if mode == "Complete Reset (including documents)"
                else "embeddings_only"
            )

            # Confirmation
            if st.button("✔️ Confirm Reset", key="confirm_reset"):
                # Get initial count for reporting
                collection = self._get_collection()
                initial_count = collection.count()

                # Perform reset
                with st.spinner("Resetting vectorstore..."):
                    if st.session_state.reset_mode == "complete":
                        # Delete all documents
                        raw_dir = Path(get_settings().RAW_DIR)
                        for file in raw_dir.glob("**/*.md"):
                            file.unlink()
                            logger.info(f"Deleted document: {file}")

                    # Reset ChromaDB
                    success, message = reset_chromadb(collection)

                    if success:
                        st.success(
                            f"Reset successful: {message}\n"
                            f"Previous state: {initial_count:,} embeddings"
                        )

                        # Force metrics update
                        st.session_state.last_metrics_update = 0
                        st.session_state.documents_loaded = False
                        st.session_state.vectorstore_initialized = False

                        # Offer reload option
                        if st.button("🔄 Reload Vectorstore", key="reload_after_reset"):
                            self._reload_vectorstore()
                    else:
                        st.error(f"Reset failed: {message}")

        except Exception as e:
            st.error(f"Reset operation failed: {e}")
            logger.error(f"Reset operation error: {e}")

    def _reload_vectorstore(self) -> None:
        """Reload vectorstore with progress tracking."""
        try:
            with st.spinner("Reloading vectorstore..."):
                # Load documents
                loader = DocumentLoader()
                documents = loader.load_documents()

                # Count source documents
                raw_docs = list(Path(get_settings().RAW_DIR).glob("**/*.md"))
                raw_count = len(raw_docs)

                # Create progress bar
                progress_text = "Processing documents..."
                progress_bar = st.progress(0, text=progress_text)

                # Create vectorstore with chunks
                vectorstore = VectorStoreManager().create_vectorstore(documents)
                chunks_count = vectorstore._collection.count()

                # Update progress
                progress_bar.progress(1.0, text="Processing complete!")

                # Show results
                st.success(
                    f"Successfully processed {raw_count:,} documents "
                    f"into {chunks_count:,} chunks"
                )

                # Update session state
                st.session_state.documents_loaded = True
                st.session_state.vectorstore_initialized = True

                # Force metrics update
                st.session_state.last_metrics_update = 0

                logger.info(
                    f"Vectorstore reloaded: {raw_count} docs, {chunks_count} chunks"
                )

        except Exception as e:
            st.error(f"Failed to reload vectorstore: {e}")
            logger.error(f"Vectorstore reload error: {e}")

    def _handle_document_upload(self, uploaded_files: list[UploadedFile]) -> None:
        """Handle document upload with progress tracking."""
        if not uploaded_files:
            return

        try:
            raw_dir = Path(get_settings().RAW_DIR)

            # Create progress tracking
            progress_text = "Processing uploads..."
            progress_bar = st.progress(0, text=progress_text)

            total_files = len(uploaded_files)
            processed = 0
            failed = 0

            for idx, file in enumerate(uploaded_files):
                try:
                    # Save file
                    save_path = raw_dir / file.name
                    save_path.write_bytes(file.getvalue())
                    processed += 1

                    # Update progress
                    progress = (idx + 1) / total_files
                    progress_bar.progress(
                        progress,
                        text=f"Processing {file.name}... ({processed}/{total_files})",
                    )

                except Exception as e:
                    failed += 1
                    logger.error(f"Failed to save {file.name}: {e}")

            # Show results
            if processed > 0:
                st.success(f"Successfully processed {processed} files")
                if st.button("Reload Vectorstore", key="reload_after_upload"):
                    self._reload_vectorstore()

            if failed > 0:
                st.error(f"Failed to process {failed} files")

        except Exception as e:
            st.error(f"Upload processing failed: {e}")
            logger.error(f"Document upload error: {e}")

    def _display_settings_tab(self) -> None:
        """Display current RAG configuration values."""
        st.subheader("RAG Configuration")

        try:
            config = get_current_configuration()

            # Group parameters by category
            categories = {
                "LLM Settings": [
                    "OLLAMA_BASE_URL",
                    "OLLAMA_TIMEOUT",
                    "LLM_MODEL",
                    "EMBEDDING_MODEL",
                    "LLM_TEMPERATURE",
                    "LLM_NUM_CTX",
                    "LLM_TOP_K",
                    "LLM_TOP_P",
                ],
                "Text Processing": [
                    "CHUNK_SIZE",
                    "CHUNK_OVERLAP",
                    "SPLIT_METHOD",
                ],
                "Scoring Weights": [
                    "SIMILARITY_WEIGHT",
                    "RELEVANCE_WEIGHT",
                    "COVERAGE_WEIGHT",
                    "COHERENCE_WEIGHT",
                    "COMPLETENESS_WEIGHT",
                    "CONSISTENCY_WEIGHT",
                ],
                "Scoring Thresholds": [
                    "MIN_ACCEPTABLE_SCORE",
                    "EXCELLENT_SCORE",
                    "CONTRADICTION_PENALTY",
                    "QUESTION_KEYWORDS_WEIGHT",
                    "CONTEXT_MATCH_WEIGHT",
                ],
                "Answer Settings": [
                    "MIN_ANSWER_LENGTH",
                    "OPTIMAL_ANSWER_LENGTH",
                ],
            }

            # Parameter descriptions
            param_descriptions = {
                "SIMILARITY_WEIGHT": "Weight for semantic similarity "
                "between query and context",
                "RELEVANCE_WEIGHT": "Weight for relevance of context to query",
                "COVERAGE_WEIGHT": "Weight for how well context covers query topics",
                "COHERENCE_WEIGHT": "Weight for logical flow and consistency",
                "COMPLETENESS_WEIGHT": "Weight for answer completeness",
                "CONSISTENCY_WEIGHT": "Weight for internal consistency",
                "MIN_ACCEPTABLE_SCORE": "Minimum score threshold for valid responses",
                "EXCELLENT_SCORE": "Score threshold for high-quality responses",
                "CONTRADICTION_PENALTY": "Penalty factor for contradictory information",
                "QUESTION_KEYWORDS_WEIGHT": "Weight for matching question keywords",
                "CONTEXT_MATCH_WEIGHT": "Weight for context relevance matching",
                "MIN_ANSWER_LENGTH": "Minimum acceptable answer length in characters",
                "OPTIMAL_ANSWER_LENGTH": "Target answer length in characters",
            }

            # Create tabs for each category
            tabs = st.tabs(list(categories.keys()))

            for tab, (category, param_names) in zip(
                tabs, categories.items(), strict=True
            ):
                with tab:
                    # Filter parameters for this category
                    category_params = {
                        param.name: param
                        for param in config.parameters.values()
                        if param.name in param_names
                    }

                    if not category_params:
                        st.info(f"No parameters found for {category}")
                        continue

                    # Create a clean table layout
                    for param_name, param in category_params.items():
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown(f"**{param_name}**")
                        with col2:
                            st.code(str(param.value), language="python")

                        # Use custom description if available
                        description = param_descriptions.get(
                            param_name, param.description
                        )
                        st.markdown(f"_{description}_")
                        st.markdown("---")

            # Export button at the bottom
            if st.button("📥 Export Configuration", type="secondary"):
                with st.spinner("Exporting configuration..."):
                    success, message = export_configuration()
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        except Exception as e:
            st.error("Failed to load configuration")
            logger.error(f"Configuration load error: {e}")

    def _display_metrics_tab(self) -> None:
        """Display system metrics with auto-refresh."""
        st.subheader("System Metrics")

        # Initialize session state if needed
        if "last_metrics_update" not in st.session_state:
            st.session_state.last_metrics_update = 0
        if "metrics" not in st.session_state:
            st.session_state.metrics = None

        # Simple refresh button
        if st.button("🔄 Refresh Now", key="refresh_metrics", type="primary"):
            st.session_state.last_metrics_update = 0

        try:
            # Always update if refresh clicked or no metrics yet
            if (
                st.session_state.last_metrics_update == 0
                or "metrics" not in st.session_state
            ):
                with st.spinner("Updating metrics..."):
                    collection = self._get_collection()

                    # Get system status
                    ollama_status, ollama_msg = asyncio.run(check_ollama_health())
                    chroma_status, chroma_msg = check_chromadb_health(collection)

                    # Display status indicators
                    status_col1, status_col2 = st.columns(2)
                    with status_col1:
                        status_icon = (
                            "🟢" if ollama_status == SystemStatus.HEALTHY else "🔴"
                        )
                        st.markdown(f"**Ollama Status**: {status_icon} {ollama_msg}")
                    with status_col2:
                        status_icon = (
                            "🟢" if chroma_status == SystemStatus.HEALTHY else "🔴"
                        )
                        st.markdown(f"**ChromaDB Status**: {status_icon} {chroma_msg}")

                    # Get memory usage
                    process = psutil.Process()
                    memory_info = process.memory_info()
                    memory_percent = process.memory_percent()

                    # Display memory metrics
                    st.subheader("Memory Usage")
                    memory_text = (
                        f"Memory: {memory_info.rss / 1024 / 1024:.1f}MB "
                        f"({memory_percent:.1f}%)"
                    )
                    st.progress(
                        memory_percent / 100,
                        text=memory_text,
                    )

                    # Collection stats
                    st.subheader("Collection Statistics")
                    count = collection.count()
                    st.markdown(f"Total embeddings: **{count:,}**")

                    # Update timestamp and store metrics
                    st.session_state.last_metrics_update = time.time()
                    st.session_state.metrics = {
                        "ollama_status": ollama_status,
                        "chroma_status": chroma_status,
                        "memory_percent": memory_percent,
                        "embeddings_count": count,
                    }

        except Exception as e:
            st.error(f"Failed to update metrics: {e}")
            logger.error(f"Metrics update error: {e}")

    def _display_documents_tab(self) -> None:
        """Display document management interface."""
        st.subheader("Document Management")

        # File upload section
        uploaded_files = st.file_uploader(
            "Upload Markdown Documents",
            type=["md"],
            accept_multiple_files=True,
            help="Upload one or more Markdown (.md) files",
            key="doc_uploader",
        )

        if uploaded_files:
            files_df = [
                {
                    "Filename": file.name,
                    "Size": self._format_bytes(file.size),
                    "Status": "Pending",
                }
                for file in uploaded_files
            ]

            st.dataframe(
                pd.DataFrame(files_df),
                use_container_width=True,
            )

            if st.button("Process Files", type="primary", key="process_uploads"):
                self._handle_document_upload(uploaded_files)

        # Existing documents section
        st.subheader("Existing Documents")
        raw_dir = Path(get_settings().RAW_DIR)
        files = list(raw_dir.glob("**/*.md"))

        if not files:
            st.info("No documents found in the system.")
            return

        # Prepare document data
        docs_data = [
            {
                "File": file_path.name,
                "Size": self._format_bytes(file_path.stat().st_size),
                "Last Modified": pd.to_datetime(file_path.stat().st_mtime, unit="s"),
                "Path": str(file_path.relative_to(raw_dir)),
            }
            for file_path in files
        ]

        # Display documents table
        st.dataframe(
            pd.DataFrame(docs_data),
            use_container_width=True,
            column_config={
                "File": st.column_config.TextColumn(
                    "File",
                    help="Document filename",
                    width="medium",
                ),
                "Size": st.column_config.TextColumn(
                    "Size",
                    help="Document size",
                    width="small",
                ),
                "Last Modified": st.column_config.DatetimeColumn(
                    "Last Modified",
                    help="Last modification date",
                    format="D MMM YYYY, HH:mm",
                    width="medium",
                ),
            },
        )

        # Management buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "🔄 Reload Vectorstore",
                type="primary",
                key="reload_vectorstore",
            ):
                self._reload_vectorstore()

        with col2:
            if st.button("📥 Export Documents", key="export_docs"):
                self._export_documents(docs_data)

        with col3:
            if st.button(
                "🗑️ Reset Vectorstore",
                type="secondary",
                key="reset_vectorstore",
            ):
                self._handle_reset()

    def _export_documents(self, docs_data: list[dict[str, Any]]) -> None:
        """Export documents to zip file.

        Args:
            docs_data: List of document metadata dictionaries
        """
        try:
            # Create zip file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                raw_dir = Path(get_settings().RAW_DIR)
                for doc in docs_data:
                    file_path = raw_dir / doc["Path"]
                    if file_path.exists():
                        zip_file.write(file_path, doc["Path"])

            # Offer download
            zip_data = zip_buffer.getvalue()
            if len(zip_data) > 0:
                st.download_button(  # type: ignore
                    label="Download Documents",
                    data=zip_data,
                    file_name="documents.zip",
                    mime="application/zip",
                )
            else:
                st.warning("No documents to export")

        except Exception as e:
            st.error(f"Failed to export documents: {e}")
            logger.error(f"Document export error: {e}")

    def render(self) -> None:
        """Render admin page with tabs."""
        st.title("Admin Dashboard")

        # Main tabs
        tab1, tab2, tab3 = st.tabs(
            [
                "📚 Documents",
                "⚙️ Settings",
                "📊 Monitoring",
            ]
        )

        with tab1:
            self._display_documents_tab()

        with tab2:
            self._display_settings_tab()

        with tab3:
            self._display_metrics_tab()


def main() -> None:
    """Main entry point for admin page."""
    page = AdminPage()
    page.render()


if __name__ == "__main__":
    main()
