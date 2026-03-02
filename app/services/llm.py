"""
LLM adapter service.
Provides pluggable LLM interface with OpenAI and fallback options.
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables (.env) at import, but also re-check env at runtime.
load_dotenv()


def _get_openai_api_key() -> str:
    """
    Read the OpenAI API key from environment at runtime.
    This avoids 'stale' values if the env var is set after process start.
    """
    # Re-load .env if present; does not override existing env vars by default.
    load_dotenv()
    return (os.getenv("OPENAI_API_KEY") or "").strip()


class MockLLM:
    """
    Mock LLM fallback that constructs answers from retrieved chunks.
    Used when OPENAI_API_KEY is not available.
    """
    
    def __call__(self, prompt: str) -> str:
        return self.generate(prompt)
    
    def generate(self, prompt: str) -> str:
        """Generate a response based on the prompt (simple extraction)."""
        # Extract context from prompt if available
        if "Context:" in prompt and "Question:" in prompt:
            context_start = prompt.find("Context:") + len("Context:")
            context_end = prompt.find("Question:")
            context = prompt[context_start:context_end].strip()
            
            if context and len(context) > 50:
                # Return first part of context as answer
                return f"Based on the documents: {context[:500]}..."
        
        return "I found some relevant information but need an LLM to generate a proper response. Please configure OPENAI_API_KEY."


def get_llm():
    """
    Get the appropriate LLM based on configuration.
    Returns ChatOpenAI if API key exists, otherwise MockLLM.
    """
    api_key = _get_openai_api_key()
    if api_key:
        print("[LLM] Using OpenAI ChatGPT")
        from langchain_community.chat_models import ChatOpenAI
        return ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=api_key
        )
    else:
        print("[WARN] OPENAI_API_KEY not found. Using mock LLM fallback.")
        return MockLLM()


def has_openai_key() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(_get_openai_api_key())


def get_llm_mode() -> str:
    """Return the current LLM mode: 'openai' or 'mock'."""
    return "openai" if has_openai_key() else "mock"

