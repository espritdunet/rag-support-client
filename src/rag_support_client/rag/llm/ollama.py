"""
LLM module for RAG Support application.
Handles language model configuration and chain creation using LangChain v0.3 LCEL.

Returns:
    Configured RAG chain with Ollama LLM
"""

from typing import Any

from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_ollama import OllamaLLM

from rag_support_client.config.config import get_settings
from rag_support_client.utils.conversation import ConversationManager
from rag_support_client.utils.logger import logger

settings = get_settings()


def get_llm() -> OllamaLLM:
    """Initialize Ollama LLM with configuration settings"""
    return OllamaLLM(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
    )


def create_chain(
    vectorstore: Chroma,
    conversation_manager: ConversationManager | None = None,
) -> RunnableParallel:
    """Create RAG chain with conversation management"""

    try:
        # Initialize LLM
        llm = get_llm()

        # Create retriever from vectorstore
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": settings.SIMILARITY_TOP_K}
        )

        # Create prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", settings.RAG_SYSTEM_TEMPLATE),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", settings.DOCUMENT_FUSION_TEMPLATE),
            ]
        )

        def process_query(input_dict: dict[str, Any]) -> dict[str, Any]:
            # Get documents
            docs = retriever.invoke(input_dict["question"])

            # Get chat history if available
            chat_history = []
            if conversation_manager and input_dict.get("session_id"):
                chat_history = conversation_manager.get_history(
                    str(input_dict["session_id"])
                )[
                    -12:
                ]  # Last 6 exchanges

            # Prepare prompt variables
            prompt_vars = {
                "chat_history": chat_history,
                "question": input_dict["question"],
                "context": "\n\n".join(doc.page_content for doc in docs),
            }

            # Get LLM response
            messages = prompt.invoke(prompt_vars).to_messages()
            response = llm.invoke(messages)

            return {
                "response": response,
                "source_documents": docs,
            }

        # Create chain
        chain = RunnableParallel(
            {
                "result": RunnableLambda(process_query),
            }
        )

        logger.info(f"Created RAG chain (k={settings.SIMILARITY_TOP_K})")
        return chain

    except Exception as e:
        logger.error(f"Chain creation error: {str(e)}")
        raise
