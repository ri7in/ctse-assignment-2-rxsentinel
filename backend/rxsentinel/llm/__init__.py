"""LLM clients — wraps Ollama for agent use."""
from rxsentinel.llm.ollama_client import OllamaClient, get_ollama_client

__all__ = ["OllamaClient", "get_ollama_client"]
