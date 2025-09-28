"""
Direct LLM Service - Bypass complex router for reliable AI responses
Uses working Anthropic Claude API directly
"""

import os
import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

class DirectLLMService:
    """Direct LLM service that uses working APIs without complex routing"""
    
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        logger.info(f"Direct LLM Service initialized:")
        logger.info(f"  Anthropic: {'✅' if self.anthropic_key else '❌'}")
        logger.info(f"  OpenAI: {'✅' if self.openai_key else '❌'}")
        logger.info(f"  Google: {'✅' if self.google_key else '❌'}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model_preference: str = "anthropic",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate response using the best available model
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model_preference: "anthropic", "openai", or "google"
            **kwargs: Additional parameters
            
        Returns:
            Dict with 'content', 'model_used', 'usage', etc.
        """
        
        # Try models in order of preference
        models_to_try = []
        
        if model_preference == "anthropic" and self.anthropic_key:
            models_to_try.append(("anthropic", "claude-3-5-sonnet-20240620"))
        elif model_preference == "openai" and self.openai_key:
            models_to_try.append(("openai", "gpt-4o-mini"))
        elif model_preference == "google" and self.google_key:
            models_to_try.append(("google", "gemini-pro"))
        
        # Add fallbacks
        if self.anthropic_key and ("anthropic", "claude-3-5-sonnet-20240620") not in models_to_try:
            models_to_try.append(("anthropic", "claude-3-5-sonnet-20240620"))
        if self.openai_key and ("openai", "gpt-4o-mini") not in models_to_try:
            models_to_try.append(("openai", "gpt-4o-mini"))
        if self.google_key and ("google", "gemini-pro") not in models_to_try:
            models_to_try.append(("google", "gemini-pro"))
        
        # Try each model
        for provider, model in models_to_try:
            try:
                if provider == "anthropic":
                    result = await self._call_anthropic(messages, model, **kwargs)
                elif provider == "openai":
                    result = await self._call_openai(messages, model, **kwargs)
                elif provider == "google":
                    result = await self._call_google(messages, model, **kwargs)
                else:
                    continue
                
                if result and result.get("content"):
                    logger.info(f"✅ {provider} response generated successfully")
                    return result
                    
            except Exception as e:
                logger.warning(f"❌ {provider} failed: {e}")
                continue
        
        # If all models fail, return a helpful message
        return {
            "content": "I apologize, but I'm currently experiencing technical difficulties with my AI services. Please try again in a moment, or contact support if the issue persists.",
            "model_used": "fallback",
            "error": "All AI models unavailable",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }
    
    async def _call_anthropic(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Call Anthropic Claude API directly"""
        
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Convert messages to Anthropic format
        anthropic_messages = []
        system_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        payload = {
            "model": model,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "messages": anthropic_messages
        }
        
        if system_message:
            payload["system"] = system_message
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    content = data.get("content", [{}])[0].get("text", "")
                    usage = data.get("usage", {})
                    
                    return {
                        "content": content,
                        "model_used": f"anthropic/{model}",
                        "usage": {
                            "prompt_tokens": usage.get("input_tokens", 0),
                            "completion_tokens": usage.get("output_tokens", 0),
                            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                        }
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error {response.status}: {error_text}")
    
    async def _call_openai(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Call OpenAI API directly"""
        
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 4096)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    
                    return {
                        "content": content,
                        "model_used": f"openai/{model}",
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0)
                        }
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")
    
    async def _call_google(
        self, 
        messages: List[Dict[str, str]], 
        model: str, 
        **kwargs
    ) -> Dict[str, Any]:
        """Call Google Gemini API directly"""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.google_key}"
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            if msg["role"] != "system":  # Skip system messages for now
                contents.append({
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": kwargs.get("max_tokens", 4096)
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    usage = data.get("usageMetadata", {})
                    
                    return {
                        "content": content,
                        "model_used": f"google/{model}",
                        "usage": {
                            "prompt_tokens": usage.get("promptTokenCount", 0),
                            "completion_tokens": usage.get("candidatesTokenCount", 0),
                            "total_tokens": usage.get("totalTokenCount", 0)
                        }
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"Google API error {response.status}: {error_text}")

# Global instance
direct_llm_service = DirectLLMService()
