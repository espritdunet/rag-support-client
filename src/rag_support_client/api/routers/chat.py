"""
Chat router for RAG Support API.
Provides secure conversation endpoints with session management and RAG chain
interactions.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response, Security
from fastapi.responses import JSONResponse

from rag_support_client.api.dependencies import get_api_key
from rag_support_client.api.models.schemas import ChatRequest
from rag_support_client.rag.scoring import calculate_confidence
from rag_support_client.utils.logger import logger
from rag_support_client.utils.state import app_state

router = APIRouter(prefix="/chat", tags=["chat"])


def build_contextual_query(session_id: str, current_question: str) -> str:
    """Build a query that includes relevant conversation history"""
    history = app_state.conversation_manager.get_history(session_id)

    if not history:
        return current_question

    # Get last 6 exchanges (12 messages = 6 pairs of Q&A)
    recent_history = history[-12:]

    # Build context string
    context_parts = []

    for msg in recent_history:
        role = "Question" if msg["role"] == "human" else "Réponse"
        context_parts.append(f"{role}: {msg['content']}")

    # Add current question with explicit instruction
    context = "\n".join(context_parts)
    query = (
        "En tenant compte de cet historique de conversation:\n"
        f"{context}\n\n"
        f"Nouvelle question: {current_question}\n\n"
        "Réponds en restant dans le contexte de la conversation."
    )

    logger.debug(f"Built contextual query: {query}")
    return query


@router.post("/session")
async def create_session(
    api_key: Annotated[str, Security(get_api_key)]
) -> dict[str, str]:
    """Create new chat session with unique ID"""
    session_id = app_state.conversation_manager.create_session_id()
    logger.info(f"Created new chat session: {session_id}")
    return {"session_id": session_id}


@router.post("/{session_id}")
async def chat(
    session_id: str,
    request: ChatRequest,
    api_key: Annotated[str, Security(get_api_key)],
) -> Response:
    """Process chat request for given session"""
    try:
        logger.debug(
            f"Processing question for session {session_id}: {request.question}"
        )

        if not app_state.rag_chain:
            raise ValueError("RAG chain not initialized")

        # Build contextual query
        contextual_query = build_contextual_query(session_id, request.question)

        # Process query through RAG chain
        result = app_state.rag_chain.invoke(
            {"question": contextual_query, "session_id": session_id}
        )

        # Store the interaction in conversation history
        app_state.conversation_manager.add_message(
            session_id=session_id, role="human", content=request.question
        )
        app_state.conversation_manager.add_message(
            session_id=session_id,
            role="assistant",
            content=result["result"]["response"],
        )

        # Extract source URLs
        sources = [
            doc.metadata.get("source_url", "")
            for doc in result["result"]["source_documents"]
            if doc.metadata.get("source_url")
        ]

        # Get the title from the most relevant document
        title = "Information not found"
        if result["result"]["source_documents"]:
            title = result["result"]["source_documents"][0].metadata.get(
                "h1", "Information not found"
            )

        # Calculate confidence scores using existing scoring module
        scores = calculate_confidence(
            question=request.question,
            answer=result["result"]["response"],
            documents=result["result"]["source_documents"],
        )

        # Structure the response
        response_data = {
            "answer": {
                "title": title,
                "content": result["result"]["response"],
                "format": "markdown",
            },
            "sources": list(set(sources)),
            "confidence": {
                "score": scores["total"],
                "level": scores["quality"],
                "details": {
                    "similarity": scores["similarity"],
                    "relevance": scores["relevance"],
                    "coverage": scores["coverage"],
                    "coherence": scores["coherence"],
                    "consistency": scores["consistency"],
                    "completeness": scores["completeness"],
                    "contradictions": scores["contradictions"],
                },
            },
            "metadata": {
                "session_id": session_id,
                "question": request.question,
                "timestamp": datetime.now(UTC).isoformat(),
                "context_length": len(
                    app_state.conversation_manager.get_history(session_id)
                ),
            },
        }

        return JSONResponse(
            content=response_data, headers={"X-Content-Type-Options": "nosniff"}
        )

    except Exception as err:
        logger.error(f"Error processing question: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing your request: {str(err)}"
        ) from err


@router.delete("/{session_id}")
async def end_session(
    session_id: str,
    api_key: Annotated[str, Security(get_api_key)],
) -> dict[str, str]:
    """End chat session and cleanup history"""
    app_state.conversation_manager.clear_conversation(session_id)
    logger.info(f"Ended chat session: {session_id}")
    return {"message": "Session ended successfully"}
