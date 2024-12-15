"""
LLM package initialization.
Exports the main chain creation function.
"""

from .ollama import create_chain

__all__ = ["create_chain"]
