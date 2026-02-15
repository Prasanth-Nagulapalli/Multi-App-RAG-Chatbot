"""
LLM adapter service.
Provides pluggable LLM interface with OpenAI and fallback options.
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


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
    if OPENAI_API_KEY:
        print("[LLM] Using OpenAI ChatGPT")
        from langchain_community.chat_models import ChatOpenAI
        return ChatOpenAI(
            model_name="gpt-3.5-turbo",
            temperature=0,
            openai_api_key=OPENAI_API_KEY
        )
    else:
        print("[WARN] OPENAI_API_KEY not found. Using mock LLM fallback.")
        return MockLLM()


def has_openai_key() -> bool:
    """Check if OpenAI API key is configured."""
    return bool(OPENAI_API_KEY)

