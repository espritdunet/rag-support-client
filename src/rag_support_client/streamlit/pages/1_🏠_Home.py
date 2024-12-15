"""Home page for the RAG application with chat interface."""

import logging
from typing import Any

import streamlit as st

from rag_support_client.config.config import get_settings
from rag_support_client.streamlit import get_rag_chain
from rag_support_client.streamlit.components import Page
from rag_support_client.streamlit.types import DeltaGenerator
from rag_support_client.utils.logger import logger
from rag_support_client.utils.state import app_state

# Configure logging to show debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Print to console
        logging.FileHandler("rag_debug.log"),  # Save to file
    ],
)

settings = get_settings()


class HomePage(Page):
    """Home page component with RAG chat interface"""

    def __init__(self) -> None:
        super().__init__(title="RAG Support Assistant", icon="🏠", layout="wide")
        self._initialize_chat_state()

    def _initialize_chat_state(self) -> None:
        """Initialize chat state and history
        with a maximum of 12 messages (6 Q&A pairs)"""
        if "session_id" not in st.session_state:
            st.session_state.session_id = (
                app_state.conversation_manager.create_session_id()
            )
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        if "message_count" not in st.session_state:
            st.session_state.message_count = 0

    def _check_rag_components(self) -> bool:
        """Check if RAG components are ready to use

        Returns:
            bool: True if RAG is ready to use, False otherwise
        """
        from rag_support_client.streamlit import is_initialized

        if not is_initialized():
            st.error(
                """
                RAG components not initialized.
                Please check application logs or contact administrator.
                """
            )
            return False
        return True

    def _format_raw_response(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        """
        Format RAG chain response maintaining exact structure from ollama.py

        Args:
            raw_response: Raw response from the RAG chain

        Returns:
            dict: Formatted response with answer and sources
        """
        try:
            # Extract from result structure as defined in ollama.py
            result = raw_response.get("result", {})
            response = result.get("response", "")
            source_docs = result.get("source_documents", [])

            # Extract unique source URLs from metadata
            sources = []
            for doc in source_docs:
                if hasattr(doc, "metadata"):
                    source_url = doc.metadata.get("source_url")
                    if source_url and source_url not in sources:
                        sources.append(source_url)
                        logger.debug(f"Source URL extracted: {source_url}")

            return {
                "answer": (
                    response.content if hasattr(response, "content") else str(response)
                ),
                "sources": sources,
            }

        except Exception as e:
            logger.error(f"Response formatting error: {e}", exc_info=True)
            return {"answer": str(raw_response), "sources": []}

    def _format_display_response(self, response: dict[str, Any]) -> str:
        """Format response for display with clickable documentation links"""
        try:
            answer = response.get("answer", "")
            sources = response.get("sources", [])

            logger.debug(f"Formatting response with sources: {sources}")

            # Format the answer first
            formatted = f"{answer}\n\n"

            # Add sources if available as clickable links
            if sources:
                formatted += "\n**Sources consultées:**\n"
                for url in sources:
                    if url:
                        # Use the full URL directly
                        formatted += f"- [Documentation]({url})\n"
                        logger.debug(f"Added source link: {url}")

            logger.debug(f"Formatted response: {formatted}")
            return formatted

        except Exception as e:
            logger.error(f"Error formatting display response: {e}", exc_info=True)
            return str(response.get("answer", str(response)))

    def _display_chat_interface(self) -> None:
        """Display chat interface using the same RAG chain as FastAPI"""
        if prompt := st.chat_input("What would you like to know?"):
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    with st.spinner("Processing..."):
                        chain = get_rag_chain()
                        if chain is None:
                            raise ValueError("RAG chain initialization failed")

                        # Use same input structure as in ollama.py
                        raw_response = chain.invoke(
                            {
                                "question": prompt,
                                "session_id": st.session_state.session_id,
                                "chat_history": st.session_state.chat_history,
                            }
                        )

                        formatted_response = self._format_raw_response(raw_response)

                        # Format display with markdown as per RAG_SYSTEM_TEMPLATE
                        display_text = formatted_response["answer"]
                        if formatted_response["sources"]:
                            display_text += "\n\n**Sources consultées:**"
                            for url in formatted_response["sources"]:
                                display_text += f"\n- [Documentation]({url})"

                        # Maintain chat history limit (12 messages, 6 Q&A pairs)
                        if len(st.session_state.chat_history) >= 12:
                            # Remove oldest Q&A pair
                            st.session_state.chat_history = (
                                st.session_state.chat_history[2:]
                            )

                        st.session_state.chat_history.extend(
                            [
                                {"role": "user", "content": prompt},
                                {"role": "assistant", "content": display_text},
                            ]
                        )

                        st.markdown(display_text)

                except Exception as e:
                    logger.error(f"Chat processing error: {e}", exc_info=True)
                    st.error(f"Processing error: {str(e)}")

    def render(self) -> DeltaGenerator:
        """Render the home page"""
        st.title("Bienvenue sur l'assistant RAG Support! 👋")

        # Left column for chat
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(
                """
                Je peux vous aider à trouver rapidement des informations précises
                dans votre documentation. Posez-moi vos questions!
                """
            )

            if not self._check_rag_components():
                st.info(
                    "Le système est en cours de démarrage... "
                    "Veuillez patienter un instant ou rafraîchir la page."
                )
                return st.container()

            self._display_chat_interface()

        # Right column for help and controls
        with col2:
            if st.button("🗑️ Effacer la conversation", type="primary"):
                app_state.conversation_manager.clear_conversation(
                    st.session_state.session_id
                )
                st.rerun()

            with st.expander("Aide", expanded=False):
                st.markdown(
                    """
                    ### Comment utiliser
                    1. Tapez votre question dans la zone de chat ci-dessous
                    2. Appuyez sur Entrée ou cliquez sur le bouton pour envoyer
                    3. Attendez la réponse basée sur votre documentation

                    ### Conseils
                    - Soyez précis dans vos questions
                    - Les questions doivent porter sur la documentation chargée
                    - Utilisez un langage clair et concis
                    """
                )

        return st.container()


def main() -> None:
    """Main entry point for the home page"""
    page = HomePage()
    page.render()


if __name__ == "__main__":
    main()
