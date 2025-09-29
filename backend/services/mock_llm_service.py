"""
Mock LLM Service for Development
Provides mock responses when external APIs are unavailable
"""

import asyncio
import random
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass


@dataclass
class MockMessage:
    role: str
    content: str


class MockLLMService:
    """Mock LLM service that provides realistic medical responses for development"""

    def __init__(self):
        self.medical_responses = [
            "Based on your symptoms of chest pain and cough lasting 3 days, this could be several conditions. The combination suggests possible respiratory infection, bronchitis, or in some cases, pneumonia. I recommend: 1) Monitor your temperature, 2) Stay hydrated, 3) Rest, and 4) Seek medical attention if symptoms worsen or you develop fever, difficulty breathing, or severe chest pain.",
            "Your symptoms of chest pain and persistent cough warrant medical evaluation. This could indicate: • Upper respiratory infection • Bronchitis • Pleurisy • Less commonly, pneumonia. Please consider seeing a healthcare provider for proper examination, especially if you experience fever, shortness of breath, or worsening symptoms.",
            "Given your 3-day history of chest pain with cough, several possibilities exist: 1) Viral respiratory infection - most common, 2) Bacterial bronchitis, 3) Pneumonia - if accompanied by fever. Red flags requiring immediate care: difficulty breathing, high fever (>101.5°F), severe chest pain, or coughing up blood. Otherwise, rest, fluids, and over-the-counter pain relief may help.",
            "The combination of chest pain and cough for 3 days suggests a respiratory condition. Differential diagnosis includes: • Acute bronchitis (most likely) • Pneumonia • Pleuritis • Upper respiratory tract infection. Recommendations: Monitor symptoms closely, maintain hydration, consider seeing a physician if no improvement in 24-48 hours or if symptoms worsen.",
            "Your symptoms could indicate a respiratory infection or bronchitis. The chest pain may be from coughing or underlying inflammation. Key recommendations: 1) Rest and hydration, 2) Avoid smoking/irritants, 3) Consider honey for cough relief, 4) Seek medical care if you develop fever >100.4°F, shortness of breath, or if symptoms persist beyond a week.",
        ]

    async def generate_response(
        self, messages: List[Dict[str, str]], model_id: str = "mock-claude", **kwargs
    ) -> "MockResponse":
        """Generate a mock medical response"""

        # Simulate API delay
        await asyncio.sleep(random.uniform(1, 2))

        # Get the user's message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break

        # Select appropriate response based on keywords
        if any(
            keyword in user_message for keyword in ["chest pain", "cough", "breathing"]
        ):
            response_text = random.choice(self.medical_responses)
        elif any(
            keyword in user_message for keyword in ["fever", "temperature", "hot"]
        ):
            response_text = "Fever can be concerning. Please monitor your temperature regularly. If it exceeds 101.5°F (38.6°C) or persists for more than 24 hours, seek medical attention. Stay hydrated and rest."
        elif any(keyword in user_message for keyword in ["headache", "head", "pain"]):
            response_text = "Headaches can have various causes. Try rest, hydration, and over-the-counter pain relief. If severe, persistent, or accompanied by other symptoms like fever, vision changes, or neck stiffness, please seek medical care."
        else:
            response_text = "Thank you for sharing your symptoms. Based on what you've described, I recommend monitoring your condition closely. If symptoms persist or worsen, please consult with a healthcare provider for proper evaluation and treatment."

        return MockResponse(content=response_text, model=model_id)

    async def generate_streaming_response(
        self, messages: List[Dict[str, str]], model_id: str = "mock-claude", **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming mock response"""

        response = await self.generate_response(messages, model_id, **kwargs)

        # Stream the response word by word
        words = response.content.split()
        for i, word in enumerate(words):
            if i == 0:
                yield word
            else:
                yield " " + word
            await asyncio.sleep(0.05)  # Simulate streaming delay


@dataclass
class MockResponse:
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.usage is None:
            # Mock token usage
            self.usage = {
                "prompt_tokens": len(self.content.split()) // 2,
                "completion_tokens": len(self.content.split()),
                "total_tokens": len(self.content.split()) * 1.5,
            }


# Global mock service instance
mock_llm_service = MockLLMService()
