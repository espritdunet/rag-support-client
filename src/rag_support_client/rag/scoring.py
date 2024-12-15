"""
Enhanced confidence scoring module for RAG responses.
"""

import re
from difflib import SequenceMatcher
from typing import TypedDict

from langchain.schema import Document

from rag_support_client.config.config import get_settings
from rag_support_client.utils.logger import logger

settings = get_settings()


class ConfidenceResult(TypedDict):
    """Type definition for confidence calculation result."""

    total: float
    similarity: float
    relevance: float
    coverage: float
    coherence: float
    consistency: float
    completeness: float
    quality: str
    contradictions: list[str]


def calculate_similarity_score(documents: list[Document]) -> float:
    """
    Calculate similarity score based on ChromaDB's similarity scores.
    Implements strict filtering based on similarity threshold.

    Args:
        documents: List of retrieved documents

    Returns:
        float: Calculated similarity score
    """
    if not documents:
        return 0.0

    try:
        # Get similarity scores from metadata
        scored_docs = []
        for doc in documents:
            score = doc.metadata.get("similarity_score", 0.0)
            if isinstance(score, int | float):
                # ChromaDB returns a distance, convert to similarity
                similarity = 1.0 - min(1.0, float(score))
                # Only keep documents above threshold
                if similarity >= settings.SIMILARITY_THRESHOLD:
                    scored_docs.append((doc, similarity))

        if not scored_docs:
            return 0.0

        # Sort by similarity and keep only top document
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs[0][1]  # Return highest similarity score

    except Exception as e:
        logger.error(f"Error calculating similarity score: {str(e)}")
        return 0.0


def calculate_coherence_score(
    question: str, answer: str, documents: list[Document]
) -> float:
    """
    Calculate coherence between question and answer.

    Args:
        question: Original question
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        float: Coherence score
    """
    try:
        # Extract key terms from question
        question_terms = set(re.findall(r"\w+", question.lower()))
        answer_terms = set(re.findall(r"\w+", answer.lower()))

        # Calculate direct term overlap
        if not question_terms:
            return 0.0

        overlap_score = len(question_terms & answer_terms) / len(question_terms)

        # Check if answer directly addresses question type
        question_types = {
            "comment": ["voici", "il faut", "vous devez", "vous pouvez"],
            "pourquoi": ["car", "parce que", "puisque", "en effet"],
            "quand": ["lorsque", "pendant", "durant", "après", "avant"],
            "où": ["dans", "à", "sur", "chez"],
        }

        for q_word, expected_terms in question_types.items():
            if q_word in question.lower():
                if any(term in answer.lower() for term in expected_terms):
                    overlap_score += 0.2
                break

        # Calculate sentence structure similarity
        similarity = SequenceMatcher(None, question, answer[: len(question)]).ratio()

        return min(1.0, (overlap_score * 0.7 + similarity * 0.3))

    except Exception as e:
        logger.error(f"Error calculating coherence score: {str(e)}")
        return 0.0


def detect_contradictions(
    answer: str, documents: list[Document]
) -> tuple[float, list[str]]:
    """
    Detect potential contradictions between answer and source documents.

    Args:
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        tuple[float, list[str]]: Consistency score and list of detected contradictions
    """
    try:
        contradictions = []
        consistency_score = 1.0

        # Extract numerical values and dates from answer and documents
        answer_numbers = re.findall(r"\d+(?:\.\d+)?", answer)
        answer_dates = re.findall(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", answer)

        for doc in documents:
            doc_numbers = re.findall(r"\d+(?:\.\d+)?", doc.page_content)
            doc_dates = re.findall(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", doc.page_content)

            # Check for numerical contradictions
            for ans_num in answer_numbers:
                for doc_num in doc_numbers:
                    if (
                        ans_num != doc_num
                        and abs(float(ans_num) - float(doc_num))
                        / max(float(ans_num), float(doc_num))
                        < 0.1
                    ):
                        contradictions.append(
                            f"Potential numerical inconsistency: {ans_num} vs {doc_num}"
                        )
                        consistency_score -= settings.CONTRADICTION_PENALTY

            # Check for date contradictions
            for ans_date in answer_dates:
                for doc_date in doc_dates:
                    if ans_date != doc_date:
                        contradictions.append(
                            f"Potential date inconsistency: {ans_date} vs {doc_date}"
                        )
                        consistency_score -= settings.CONTRADICTION_PENALTY

            # Check for negation contradictions
            negation_pairs = [
                (r"ne \w+ pas", r"\w+"),
                (r"n'(?:est|était) pas", r"est|était"),
                (r"impossible", r"possible"),
                (r"jamais", r"toujours"),
            ]

            for neg_pattern, pos_pattern in negation_pairs:
                neg_in_answer = bool(re.search(neg_pattern, answer.lower()))
                pos_in_doc = bool(re.search(pos_pattern, doc.page_content.lower()))

                if neg_in_answer and pos_in_doc:
                    contradictions.append("Potential logical contradiction detected")
                    consistency_score -= settings.CONTRADICTION_PENALTY

        return max(0.0, consistency_score), contradictions

    except Exception as e:
        logger.error(f"Error detecting contradictions: {str(e)}")
        return 0.0, []


def calculate_completeness_score(
    question: str, answer: str, documents: list[Document]
) -> float:
    """
    Evaluate the completeness of the answer.

    Args:
        question: Original question
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        float: Completeness score
    """
    try:
        score = 0.0

        # Length assessment
        answer_length = len(answer)
        if answer_length < settings.MIN_ANSWER_LENGTH:
            score += 0.3
        elif answer_length <= settings.OPTIMAL_ANSWER_LENGTH:
            score += 0.8
        else:
            score += 0.6  # Penalize overly long answers

        # Check for expected answer components
        question_indicators = {
            "comment": ["étapes", "procédure", "méthode"],
            "pourquoi": ["raison", "cause", "explication"],
            "quand": ["moment", "période", "date"],
            "où": ["emplacement", "lieu", "localisation"],
        }

        for indicator_type, expected_terms in question_indicators.items():
            if indicator_type in question.lower():
                if any(term in answer.lower() for term in expected_terms):
                    score += 0.2
                break

        # Check coverage of source material key points
        key_points = set()
        for doc in documents:
            # Extract section headers or important phrases
            headers = re.findall(r"^#+\s+(.+)$", doc.page_content, re.MULTILINE)
            key_points.update(headers)

        covered_points = sum(
            1 for point in key_points if point.lower() in answer.lower()
        )
        if key_points:
            coverage_ratio = covered_points / len(key_points)
            score += coverage_ratio * 0.4

        return min(1.0, score)

    except Exception as e:
        logger.error(f"Error calculating completeness score: {str(e)}")
        return 0.0


def calculate_relevance_score(
    question: str, answer: str, documents: list[Document]
) -> float:
    """
    Calculate relevance score based on answer content and metadata.

    Args:
        question: Original question
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        float: Calculated relevance score
    """
    try:
        if not answer or answer.lower().startswith("je n'ai pas"):
            return 0.0

        score = 0.0

        # Check answer length and structure
        words = answer.split()
        if len(words) < 10:
            score += 0.2
        elif len(words) < 30:
            score += 0.6
        else:
            score += 0.8

        # Check if answer contains technical terms from context
        technical_terms = set()
        for doc in documents:
            header_path = doc.metadata.get("header_path", "")
            if header_path:
                technical_terms.update(header_path.split(" > "))

        # Count technical terms in answer
        term_count = sum(
            1 for term in technical_terms if term.lower() in answer.lower()
        )
        if term_count > 0:
            score += min(0.2, term_count * 0.05)  # Max bonus of 0.2

        return min(1.0, score)

    except Exception as e:
        logger.error(f"Error calculating relevance score: {str(e)}")
        return 0.0


def calculate_coverage_score(answer: str, documents: list[Document]) -> float:
    """
    Calculate coverage score based on answer structure and document metadata.

    Args:
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        float: Calculated coverage score
    """
    try:
        score = 0.0

        # Structure scoring
        if any(str(i) + "." in answer for i in range(10)):
            score += 0.3  # Numbered steps
        if answer.count("\n\n") > 0:
            score += 0.2  # Multiple paragraphs
        if any(p in answer for p in [",", ";", ":", "(", ")"]):
            score += 0.1  # Rich punctuation

        # Check if answer covers multiple sections from context
        covered_sections = set()
        for doc in documents:
            section = doc.metadata.get("section")
            if section:
                covered_sections.add(section)

        # Bonus for covering multiple sections
        score += min(0.4, len(covered_sections) * 0.1)

        return min(1.0, score)

    except Exception as e:
        logger.error(f"Error calculating coverage score: {str(e)}")
        return 0.0


def calculate_confidence(
    question: str, answer: str, documents: list[Document]
) -> ConfidenceResult:
    """
    Calculate comprehensive confidence scores for the response.

    Args:
        question: Original question
        answer: Generated answer
        documents: Retrieved documents

    Returns:
        ConfidenceResult: Extended confidence scores and details
    """
    try:
        # Calculate all scores
        similarity = calculate_similarity_score(documents)
        relevance = calculate_relevance_score(question, answer, documents)
        coverage = calculate_coverage_score(answer, documents)
        coherence = calculate_coherence_score(question, answer, documents)
        consistency, contradictions = detect_contradictions(answer, documents)
        completeness = calculate_completeness_score(question, answer, documents)

        # Calculate weighted total score
        total = (
            settings.SIMILARITY_WEIGHT * similarity
            + settings.RELEVANCE_WEIGHT * relevance
            + settings.COVERAGE_WEIGHT * coverage
            + settings.COHERENCE_WEIGHT * coherence
            + settings.CONSISTENCY_WEIGHT * consistency
            + settings.COMPLETENESS_WEIGHT * completeness
        )

        # Normalize total score
        weight_sum = (
            settings.SIMILARITY_WEIGHT
            + settings.RELEVANCE_WEIGHT
            + settings.COVERAGE_WEIGHT
            + settings.COHERENCE_WEIGHT
            + settings.CONSISTENCY_WEIGHT
            + settings.COMPLETENESS_WEIGHT
        )

        # Normalize the total score to get it between 0 and 1
        total = total / weight_sum if weight_sum > 0 else 0.0

        # Determine quality level
        if total >= settings.EXCELLENT_SCORE:
            quality = "excellent"
        elif total >= settings.MIN_ACCEPTABLE_SCORE:
            quality = "acceptable"
        else:
            quality = "needs_improvement"

        return {
            "total": round(total, 2),
            "similarity": round(similarity, 2),
            "relevance": round(relevance, 2),
            "coverage": round(coverage, 2),
            "coherence": round(coherence, 2),
            "consistency": round(consistency, 2),
            "completeness": round(completeness, 2),
            "quality": quality,
            "contradictions": contradictions,
        }

    except Exception as e:
        logger.error(f"Error calculating confidence scores: {str(e)}")
        error_result: ConfidenceResult = {
            "total": 0.0,
            "similarity": 0.0,
            "relevance": 0.0,
            "coverage": 0.0,
            "coherence": 0.0,
            "consistency": 0.0,
            "completeness": 0.0,
            "quality": "error",
            "contradictions": [f"Scoring error: {str(e)}"],
        }
        return error_result
