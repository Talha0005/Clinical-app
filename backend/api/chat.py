"""
Chat API endpoints and LLM router exports
"""

from services.llm_router import get_llm_router

# Export the LLM router for other modules
llm_router = get_llm_router()
